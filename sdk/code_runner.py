# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from threading import Lock

from smart_ml import SmartML


# Python 2/3 compatibility
__metaclass__ = type


class CodeRunner:

    def __init__(self, f, *args, **kwargs):
        self.f = self.wrap(f, *args, **kwargs)
        self.done = False
        self.lock = Lock()
        self.logger = logging.getLogger("hyperdash.{}".format(__name__))

    def wrap(self, f, *args, **kwargs):
        # TODO: Inject me or something
        kwargs["hyperdash"] = SmartML()

        def wrapped():
            # TODO: Error handling
            try:
                f(*args, **kwargs)
            finally:
                with self.lock:
                    self.done = True
        return wrapped

    def run(self):
        self.f()

    def is_done(self):
        with self.lock:
            return self.done
