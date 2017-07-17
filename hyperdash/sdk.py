# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import sys

from .code_runner import CodeRunner
from .hyper_dash import HyperDash
from .io_buffer import IOBuffer
from .server_manager import ServerManagerHTTP
from .server_manager import ServerManagerWAMP

import certifi


# TODO: We should probably spawn a separate process instead of using a thread
# so that it is easier to kill jobs, but that makes capturing STDOUT trickier
# so we use threads for now.


def monitor(model_name, use_http=False, api_key_getter=None):
    # Needs to happen as soon as possible so we put it here
    fix_certificate_authorities()

    def _monitor(f):

        def monitored(*args, **kwargs):
            # Buffers to which to redirect output so we can capture it
            out = [IOBuffer(), IOBuffer()]
            logging.basicConfig(stream=out[0], level=logging.INFO)

            # Capture STDOUT/STDERR before they're modified
            old_out, old_err = sys.stdout, sys.stderr

            # Redirect STDOUT/STDERR to buffers
            sys.stdout, sys.stderr = out

            if not hasattr(f, 'callcount'):
                f.callcount = 0
            if f.callcount >= 1:
                raise Exception("Hyperdash does not support recursive functions!")
            else:
                f.callcount += 1
            # TODO: Instead of just returning once the function has completed,
            # this decorator needs to act like a daemon that runs the users
            # code, but also continues to wait for instructions from a remote
            # server. So, for example, when the job is done the user could
            # trigger another run from their phone OR while the job is running
            # they could send a "stop" signal, in which case we kill the
            # thread/process and then wait for a signal to start it back up again.
            # This should be fairly easy to implement, but this is good enough
            # for demo-ing purposes.
            try:
                code_runner = CodeRunner(f, *args, **kwargs)
                hyper_dash = HyperDash(
                    model_name,
                    code_runner,
                    ServerManagerHTTP if use_http else ServerManagerWAMP,
                    out,
                    (old_out, old_err,),
                    use_http=use_http,
                    custom_api_key_getter=api_key_getter,
                )
                hyper_dash.run()
                f.callcount -= 1
            # Prevent uncaught exceptions from silently being swallowed
            except Exception:
                raise
            finally:
                # Cleanup
                sys.stdout, sys.stderr = old_out, old_err
        return monitored
    return _monitor


def fix_certificate_authorities():
    """
    In certain environments twisted looks in the wrong places for
    your trusted certificate authorities and then begins to fail silently
    whenever you try and established a TLS/SSL connection. This hack forces
    the underlying machinery to look in the right place for trusted CA's.
    https://github.com/crossbario/autobahn-python/issues/866
    https://github.com/twisted/treq/issues/94
    """
    os.environ['SSL_CERT_FILE'] = certifi.where()
