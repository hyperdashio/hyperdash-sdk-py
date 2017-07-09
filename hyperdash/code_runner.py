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
            try:
                f(*args, **kwargs)
            except Exception as e:
                self.logger.error(format_exc())
                with self.lock:
                    self.exited_cleanly = False
                raise
            finally:
                with self.lock:
                    self.done = True
        return wrapped

    def run(self):
        self.f()

    def is_done(self):
        with self.lock:
            return self.exited_cleanly, self.done
