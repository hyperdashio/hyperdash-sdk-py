# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals
from threading import Thread

import datetime
import json
import os
import sys
import time
import uuid

from six.moves.queue import Queue
from six import PY2
from slugify import slugify

from .code_runner import CodeRunner
from .constants import get_hyperdash_logs_home_path
from .constants import get_hyperdash_logs_home_path_for_job
from .constants import MAX_LOG_SIZE_BYTES
from .sdk_message import create_run_started_message
from .sdk_message import create_run_ended_message
from .sdk_message import create_log_message
from .utils import human_readable_duration

# Python 2/3 compatibility
__metaclass__ = type


INFO_LEVEL = 'INFO'
ERROR_LEVEL = 'ERROR'


class HyperDash:
    """HyperDash monitors a job and manages capturing IO / server comms.

    This class is designed to be run in its own thread and contains an instance
    of runner (which is running the job) and server_manager (for talking
    to the server.)
    """

    def __init__(
        self,
        job_name,
        current_sdk_run_uuid,
        server_manager,
        io_bufs,
        std_streams,
        parent_logger,
        runner,
    ):
        """Initialize the HyperDash class.

        args:
            1) job_name: Name of the current running job
            2) current_sdk_run_uuid: UUID of current run
            3) runner: Instance of CodeRunner or ExperimentRunner
            4) server_manager: ServerManager instance
            5) io_bufs: Tuple in the form of (StringIO(), StringIO(),)
            6) std_streams: Tuple in the form of (StdOut, StdErr)
        """
        self.job_name = job_name
        self.current_sdk_run_uuid = current_sdk_run_uuid
        self.runner = runner
        self.server_manager = server_manager
        self.out_buf, self.err_buf = io_bufs
        self.std_out, self.std_err = std_streams
        self.programmatic_exit = False
        self.shutdown_network_channel = Queue()
        self.shutdown_main_channel = Queue()

        # Used to keep track of the current position in the IO buffers for data
        # that has been sent to STDOUT/STDERR and the logfile
        self.out_buf_offset = 0
        self.err_buf_offset = 0

        # Used to keep track of the current position in the IO buffers for data
        # that has been sent to the ServerManager. We separate the local/server
        # offsets because in the case of the user's code frequently flushing, we
        # want terminal/logs to update extremely quickly, but a small delay in
        # sending data to the server is acceptable so that more data can be batched
        # together. I.E if the user's code flushes 1000 times per second, we want
        # to capture that in realtime locally, but only want to send one message to
        # the server with the cumulative output of those 1000 flushes for the one
        # second period.
        self.server_out_buf_offset = 0
        self.server_err_buf_offset = 0

        self.time_since_last_server_capture = time.time()

        # Create run_start message before doing any other setup work to make sure that the
        # run_started message always precedes any other messages
        self.server_manager.put_buf(
            create_run_started_message(
                self.current_sdk_run_uuid, self.job_name),
        )

        def on_stdout_flush():
            self.capture_io()
            self.std_out.flush()
            self.flush_log_file()

        def on_stderr_flush():
            self.capture_io()
            self.std_err.flush()
            self.flush_log_file()

        self.out_buf.set_on_flush(on_stdout_flush)
        self.err_buf.set_on_flush(on_stderr_flush)

        self.logger = parent_logger.getChild(__name__)
        self.log_file, self.log_file_path = self.open_log_file()
        if not self.log_file:
            self.logger.error(
                "Could not create logs file. Logs will not be stored locally.")

    def open_log_file(self):
        log_folder = get_hyperdash_logs_home_path()

        # Make sure logs directory exists (/logs)
        if not os.path.exists(log_folder):
            try:
                os.makedirs(log_folder)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    pass
                return None, None

        job_log_folder = get_hyperdash_logs_home_path_for_job(self.job_name)
        # Make sure directory for job exists in log directory (/logs/<JOB_NAME>)
        if not os.path.exists(job_log_folder):
            try:
                os.makedirs(job_log_folder)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    pass
                return None, None

        # Create new log file for run
        try:
            iso = slugify(datetime.datetime.now().isoformat())
            logfile_name = "{}_{}.log".format(slugify(self.job_name), iso)
            logfile_path = os.path.join(job_log_folder, logfile_name)
            return open(logfile_path, "a"), logfile_path
        except IOError:
            return None, None

    # Capture all IO for terminal/log file since we last checked
    def capture_io(self, force_server_capture=False):
        current_time = time.time()
        should_send_to_server_manager = (
            ((current_time - self.time_since_last_server_capture) > 1) or
            force_server_capture
        )
        if should_send_to_server_manager:
            self.time_since_last_server_capture = current_time

        self.out_buf.acquire()
        out = self.out_buf.getvalue()
        # Local
        len_out = len(out) - self.out_buf_offset
        if len_out != 0:
            self.print_out(out[self.out_buf_offset:])
        self.out_buf_offset += len_out
        # Server
        len_out_server = len(out) - self.server_out_buf_offset
        if len_out_server != 0 and should_send_to_server_manager:
            self.send_print_to_server_manager(
                out[self.server_out_buf_offset:], INFO_LEVEL)
            self.server_out_buf_offset += len_out_server
        self.out_buf.release()

        self.err_buf.acquire()
        err = self.err_buf.getvalue()
        # Local
        len_err = len(err) - self.err_buf_offset
        if len_err != 0:
            self.print_err(err[self.err_buf_offset:])
        self.err_buf_offset += len_err
        # Server
        len_err_server = len(err) - self.server_err_buf_offset
        if len_err_server != 0 and should_send_to_server_manager:
            self.send_print_to_server_manager(
                err[self.server_err_buf_offset:], ERROR_LEVEL)
            self.server_err_buf_offset += len_err_server
        self.err_buf.release()

    def print_out(self, s):
        self.std_out.write(s)
        self.write_to_log_file(s)

    def print_err(self, s):
        self.std_err.write(s)
        self.write_to_log_file(s)

    # In the case that the amount of data is large, we chunk it into
    # several smaller messages
    def send_print_to_server_manager(self, s, level):
        offset = 0
        while offset < len(s):
            chunk_size = min(len(s) - offset, MAX_LOG_SIZE_BYTES)
            message = create_log_message(
                self.current_sdk_run_uuid, level, s[offset:offset + chunk_size])
            self.server_manager.put_buf(message)
            offset += chunk_size

    def write_to_log_file(self, s):
        if self.log_file:
            if PY2:
                self.log_file.write(s.encode("utf-8"))
            else:
                self.log_file.write(s)

    def flush_log_file(self):
        if self.log_file:
            self.log_file.flush()

    def cleanup(self, exit_status):
        self.print_completion_message()
        self.capture_io(force_server_capture=True)
        self.server_manager.put_buf(
            create_run_ended_message(self.current_sdk_run_uuid, exit_status),
        )
        self.flush_log_file()
        self.shutdown_network_channel.put(True)

    def sudden_cleanup(self):
        self.print_completion_message()
        # Send what we can to local log
        self.capture_io()
        self.flush_log_file()

        # Make a best-effort attempt to notify server that the run was
        # canceled by the user, but don't wait for all messages to
        # be flushed to server so we don't hang the user's terminal.
        self.server_manager.send_message(
            create_run_ended_message(
                self.current_sdk_run_uuid, "user_canceled"),
            raise_exceptions=False,
            timeout_seconds=1,
        )
        # Prevent the network thread from continuing to run in the background
        # even if SystemExit is caught
        self.shutdown_network_channel.put(True)

    def print_completion_message(self):
        start_time, end_time = self.runner.get_start_and_end_time()
        # end_time is not set in the case that the user canceled the run
        if not end_time:
            end_time = datetime.datetime.now()

        if self.log_file_path:
            self.logger.info("This run of {} ran for {} and logs are available locally at: {}".format(
                self.job_name,
                human_readable_duration(start_time, end_time),
                self.log_file_path,
            ))

    def run(self):
        """
        run_http works using three separate threads:
            1) runner thread which runs the user's code (if using CodeRunner)
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

        network_thread = Thread(target=network_loop)
        # Daemonize so they don't impede shutdown if the user
        # keyboard interrupts
        network_thread.daemon = True
        network_thread.start()

        # Create thread for running code if using CLI or decorator
        if self.runner.should_run_as_thread():
            code_thread = Thread(target=self.runner.run)
            code_thread.daemon = True
            code_thread.start()
            
        # Event loop
        while True:
            try:
                self.capture_io()
                exited_cleanly, is_done = self.runner.is_done()
                if is_done:
                    self.programmatic_exit = True
                    if exited_cleanly:
                        self.cleanup("success")
                        # Block until network loop says its done
                        self.shutdown_main_channel.get(
                            block=True, timeout=None)
                        return self.runner.get_return_val()
                    else:
                        self.cleanup("failure")
                        # Block until network loop says its done
                        self.shutdown_main_channel.get(
                            block=True, timeout=None)
                        raise self.runner.get_exception()

                time.sleep(1)
            # Handle Ctrl+C
            except (KeyboardInterrupt, SystemExit):
                self.sudden_cleanup()
                # code_thread and network_thread are daemons so they won't impede this
                sys.exit(130)
