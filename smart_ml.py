# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals


# Python 2/3 compatibility
__metaclass__ = type


class SmartML:
    def get_param(self, key, default):
        """
        Return a value associated with a given key.

        Useful for changing the values of parameters between runs.
        """
        # TODO: Get value from server and fallback to default
        return 3

    def emit_stat(self, key, val):
        """
        Emit a stat for a given key.

        Useful for counting the occurence of things.
        """
        raise NotImplemented()

    def start_timer(self, key):
        """
        Begin timing a sequence of code.

        Useful for measuring how long certain parts of your script take.
        """
        raise NotImplemented()

    def stop_timer(self, key):
        """Stop timing a sequence of code."""
        raise NotImplemented()
