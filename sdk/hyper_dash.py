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
        code_runner,
        server_manager,
        io_bufs,
        std_streams,
        custom_api_key_getter=None,
    ):
        """Initialize the HyperDash class.

        args:
            1) code_runner: Instance of CodeRunner
            2) server_manager: Instance of ServerManager
            3) io_bufs: Tuple in the form of (StringIO(), StringIO(),)
            4) std_streams: Tuple in the form of (StdOut, StdErr)
            5) get_api_key: Optional function which when called returns an API key as a string
        """
        self.code_runner = code_runner
        self.server_manager = server_manager
        self.out_buf, self.err_buf = io_bufs
        self.std_out, self.std_err = std_streams

        # Used to keep track of the current position in the IO buffers
        self.out_buf_offset = 0
        self.err_buf_offset = 0

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
                'timestamp': int(time.time()),
                'uuid': str(uuid.uuid4()),
                'level': level,
                'body': body,
            }
        )

    def create_sdk_message(self, typeStr, payload):
        """Create a structured message for the server."""
        return json.dumps({
            'type': typeStr,
            'payload': payload,
        })

    def cleanup(self):
        self.server_manager.cleanup()

    def run(self):
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
