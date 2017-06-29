# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals
from threading import Thread

import json
import logging
import time
import uuid

# Python 2/3 compatibility
__metaclass__ = type

TYPE_LOG = 'log'
TYPE_STARTED = 'run_started'
TYPE_ENDED = 'run_ended'

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
        custom_api_key_getter=None,
    ):
        """Initialize the HyperDash class.

        args:
            1) job_name: Name of the current running job
            2) code_runner: Instance of CodeRunner
            3) server_manager: Instance of ServerManager
            4) io_bufs: Tuple in the form of (StringIO(), StringIO(),)
            5) std_streams: Tuple in the form of (StdOut, StdErr)
            6) custom_api_key_getter: Optional function which when called returns an API key as a string
        """
        self.job_name = job_name
        self.code_runner = code_runner
        self.server_manager = server_manager
        self.out_buf, self.err_buf = io_bufs
        self.std_out, self.std_err = std_streams

        # Used to keep track of the current position in the IO buffers
        self.out_buf_offset = 0
        self.err_buf_offset = 0

        # SDK-generated run UUID
        self.current_sdk_run_uuid = None

        # TODO: Support file
        self.logger = logging.getLogger("hyperdash.{}".format(__name__))

    def capture_io(self):
        out = self.out_buf.getvalue()
        err = self.err_buf.getvalue()

        len_out = len(out) - self.out_buf_offset
        len_err = len(err) - self.err_buf_offset

        self.print_out(out[self.out_buf_offset:]) if len_out != 0 else None
        self.print_err(err[self.err_buf_offset:]) if len_err != 0 else None

        self.out_buf_offset += len_out
        self.err_buf_offset += len_err

    def print_out(self, s):
        message = self.create_log_message(INFO_LEVEL, s)
        self.server_manager.put_buf(message)
        print(s, file=self.std_out)

    def print_err(self, s):
        message = self.create_log_message(ERROR_LEVEL, s)
        self.server_manager.put_buf(message)
        print(s, file=self.std_err)

    def create_log_message(self, level, body):
        return self.create_sdk_message(
            TYPE_LOG,
            {
                'uuid': str(uuid.uuid4()),
                'level': level,
                'body': body,
            }
        )

    def create_run_started_message(self):
        return self.create_sdk_message(
            TYPE_STARTED,
            {
                'job_name': self.job_name,
            },
        )

    def create_sdk_message(self, typeStr, payload):
        """Create a structured message for the server."""
        return json.dumps({
            'type': typeStr,
            'timestamp': int(time.time()),
            'sdk_run_uuid': self.current_sdk_run_uuid,
            'payload': payload,
        })

    def cleanup(self):
        self.server_manager.cleanup()

    def run(self):
        # Create a UUID to uniquely identify this run from the SDK's point of view
        self.current_sdk_run_uuid = str(uuid.uuid4())
        # Notify the server that a new run has started
        self.server_manager.put_buf(self.create_run_started_message())

        # Start running the user's code
        code_thread = Thread(target=self.code_runner.run)
        code_thread.start()

        try:
            # Event-loop
            while True:
                self.capture_io()
                self.server_manager.tick()
                if self.code_runner.is_done():
                    self.cleanup()
                    return
                # TODO: Make sleep decision based on time since last
                # tick
                time.sleep(1)
        except Exception as e:
            self.print_out(e)
            self.print_err(e)
            return e
