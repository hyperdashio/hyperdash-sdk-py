# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
from inspect import getargspec
from threading import Lock
from traceback import format_exc


# Python 2/3 compatibility
__metaclass__ = type


class CodeRunner:

    def __init__(self, f, hd_client, parent_logger, *args, **kwargs):
        self.logger = parent_logger.getChild(__name__)
        self.hd_client = hd_client
        self.f = self.wrap(f, *args, **kwargs)
        self.done = False
        self.exited_cleanly = True
        self.return_val = None
        self.exception = None
        self.lock = Lock()
        self.start_time = None
        self.end_time = None

    def wrap(self, f, *args, **kwargs):
        arg_spec = getargspec(f)
        # Make sure function signature can handle injected hyperdash object
        if "exp" in arg_spec.args or arg_spec.keywords:
            # TODO: Inject in constructor instead of instantiating here
            kwargs["exp"] = self.hd_client

        def wrapped():
            # TODO: Error handling
            return_val = None
            try:
                self.start_time = datetime.now()
                return_val = f(*args, **kwargs)
                self.end_time = datetime.now()
            except Exception as e:
                self.logger.error(format_exc())
                with self.lock:
                    self.exited_cleanly = False
                    self.exception = e
            finally:
                with self.lock:
                    self.done = True
                    self.return_val = return_val
        return wrapped

    def run(self):
        self.f()

    def is_done(self):
        with self.lock:
            return self.exited_cleanly, self.done

    def get_return_val(self):
        with self.lock:
            return self.return_val

    def get_exception(self):
        with self.lock:
            return self.exception

    def should_run_as_thread(self):
        return True

    def get_start_and_end_time(self):
        with self.lock:
            return self.start_time, self.end_time
