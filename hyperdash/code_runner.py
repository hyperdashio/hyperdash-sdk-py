# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

from inspect import getargspec
import logging
from threading import Lock
from traceback import format_exc

from .smart_ml import SmartML


# Python 2/3 compatibility
__metaclass__ = type


class CodeRunner:

    def __init__(self, f, *args, **kwargs):
        self.f = self.wrap(f, *args, **kwargs)
        self.done = False
        self.exited_cleanly = True
        self.return_val = None
        self.exception = None
        self.lock = Lock()
        self.logger = logging.getLogger("hyperdash.{}".format(__name__))

    def wrap(self, f, *args, **kwargs):
        arg_spec = getargspec(f)
        # Make sure function signature can handle injected hyperdash object
        if 'hyperdash' in arg_spec.args or arg_spec.keywords:
            # TODO: Inject in constructor instead of instantiating here
            kwargs["hyperdash"] = SmartML()

        def wrapped():
            # TODO: Error handling
            return_val = None
            try:
                return_val = f(*args, **kwargs)
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
