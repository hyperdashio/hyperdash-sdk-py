# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals
from threading import Thread

import json
import logging
import sys
import time
import uuid

from six.moves.queue import Queue

from .sdk_message import create_run_started_message
from .sdk_message import create_run_ended_message
from .sdk_message import create_log_message


# Python 2/3 compatibility
__metaclass__ = type


INFO_LEVEL = 'INFO'
ERROR_LEVEL = 'ERROR'


class HyperDash:
    """HyperDash monitors a job and manages capturing IO / server comms.

    This class is designed to be run in its own thread and contains an instance
    of code_runner (which is running the job) and server_manager (for talking
    to the server.)
    """

    def __init__(
        self,
        job_name,
        code_runner,
        server_manager,
        io_bufs,
        std_streams,
    ):
        """Initialize the HyperDash class.

        args:
            1) job_name: Name of the current running job
            2) code_runner: Instance of CodeRunner
            3) server_manager: ServerManager instance
            4) io_bufs: Tuple in the form of (StringIO(), StringIO(),)
            5) std_streams: Tuple in the form of (StdOut, StdErr)
        """
        self.job_name = job_name
        self.code_runner = code_runner    
        self.server_manager = server_manager
        self.out_buf, self.err_buf = io_bufs
        self.std_out, self.std_err = std_streams
        self.programmatic_exit = False
        self.shutdown_network_channel = Queue()
        self.shutdown_main_channel = Queue()

        # Used to keep track of the current position in the IO buffers
        self.out_buf_offset = 0
        self.err_buf_offset = 0

        # SDK-generated run UUID
        self.current_sdk_run_uuid = None

        def on_stdout_flush():
            self.capture_io()
            self.std_out.flush()

        def on_stderr_flush():
            self.capture_io()
            self.std_err.flush()

        self.out_buf.set_on_flush(on_stdout_flush)
        self.err_buf.set_on_flush(on_stderr_flush)

        # TODO: Support file
        self.logger = logging.getLogger("hyperdash.{}".format(__name__))

    def capture_io(self):
        self.out_buf.acquire()
        out = self.out_buf.getvalue()
        len_out = len(out) - self.out_buf_offset
        self.print_out(out[self.out_buf_offset:]) if len_out != 0 else None
        self.out_buf_offset += len_out
        self.out_buf.release()

        self.err_buf.acquire()
        err = self.err_buf.getvalue()
        len_err = len(err) - self.err_buf_offset
        self.print_err(err[self.err_buf_offset:]) if len_err != 0 else None
        self.err_buf_offset += len_err
        self.err_buf.release()

    def print_out(self, s):
        message = create_log_message(self.current_sdk_run_uuid, INFO_LEVEL, s)
        self.server_manager.put_buf(message)
        self.std_out.write(s)

    def print_err(self, s):
        message = create_log_message(self.current_sdk_run_uuid, ERROR_LEVEL, s)
        self.server_manager.put_buf(message)
        self.std_err.write(s)

    def cleanup_http(self, exit_status):
        self.capture_io()
        self.server_manager.put_buf(
            create_run_ended_message(self.current_sdk_run_uuid, exit_status),
        )
        self.shutdown_network_channel.put(True)

    def run(self):
        # Create a UUID to uniquely identify this run from the SDK's point of view
        self.current_sdk_run_uuid = str(uuid.uuid4())

        # Create run_start message before doing any other setup work to make sure that the
        # run_started message always precedes any other messages
        self.server_manager.put_buf(
            create_run_started_message(self.current_sdk_run_uuid, self.job_name),
        )

        return self.run_http()

    def run_http(self):
        """
        run_http works using three separate threads:
            1) code_runner thread which runs the user's code
            2) network_thread which does blocking I/O with the server
            3) event_loop thread which runs the SDK's main event loop (this is
               just the main thread)

        We require the event loop and network loop to be in separate threads
        because otherwise slow responses from the server could inhibit the
        SDK's event loop causing weird behavior like delayed logs in the user's
        terminal.

        Once all threads are running, the event_loop thread will periodically
        check the I/O buffers to see if any new logs have appeared, and if so,
        it will send them to the server manager's outgoing buffer.

        The network_loop thread will periodically check its outgoing buffer, and
        if it finds any messages in there, it will send them all to the server.

        Cleanup is the responsibility of the event_loop. With every tick of the
        event_loop, we check to see if the user's code has completed running. If
        it has, the event_loop will capture any remaining I/O and store that in
        the ServerManager's outgoing buf, as well as store a message indicating
        that the run is complete and its final exit status. Finally, the
        event_loop thread will push a message into the shutdown_network_channel which
        will indicate to the network_loop that it should finish sending any
        pending messages and then exit. The event_loop thread will then block
        until it receives a message on the shutdown_main_channel.

        At the next tick of the network_loop, the shutdown_network_channel will no longer
        be empty, and the network loop will try and fire off any remaining messages
        in the ServerManager's buffer to the server, and then put a message in the
        shutdown_main_channel.

        The main event_loop which has been blocked until now on the shutdown_main_channel
        will now return, and the program will exit cleanly.
        """
        def network_loop():
            while True:
                if self.shutdown_network_channel.qsize() != 0:
                    self.server_manager.cleanup(self.current_sdk_run_uuid)
                    self.shutdown_main_channel.put(True)
                    return
                else:
                    self.server_manager.tick(self.current_sdk_run_uuid)
                    time.sleep(1)

        code_thread = Thread(target=self.code_runner.run)
        network_thread = Thread(target=network_loop)

        # Daemonize them so they don't impede shutdown if the user
        # keyboard interrupts
        code_thread.daemon=True
        network_thread.daemon=True
      
        network_thread.start()
        code_thread.start()

        # Event loop
        while True:
            try:
                self.capture_io()
                exited_cleanly, is_done = self.code_runner.is_done()
                if is_done:
                    self.programmatic_exit = True
                    if exited_cleanly:
                        self.cleanup_http("success")
                        # Block until network loop says its done
                        self.shutdown_main_channel.get(block=True, timeout=None)
                        return self.code_runner.get_return_val()
                    else:
                        self.cleanup_http("failure")
                        # Block until network loop says its done
                        self.shutdown_main_channel.get(block=True, timeout=None)
                        raise self.code_runner.get_exception()

                time.sleep(1)
            # Handle Ctrl+C
            except (KeyboardInterrupt, SystemExit):
                # TODO: Set low timeout here
                # 
                self.server_manager.send_message(
                    create_run_ended_message(self.current_sdk_run_uuid, "user_canceled"),
                    raise_exceptions=False
                )
                # code_thread and network_thread are daemons so they won't impede this
                sys.exit(130)
