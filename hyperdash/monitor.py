# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import uuid

from .client import HDClient
from .code_runner import CodeRunner
from .constants import API_NAME_MONITOR
from .hyper_dash import HyperDash
from .io_buffer import IOBuffer
from .server_manager import ServerManagerHTTP
from .utils import get_logger


def monitor(model_name, api_key_getter=None, capture_io=True):
    return _monitor(model_name, api_key_getter, capture_io, API_NAME_MONITOR)


def _monitor(model_name, api_key_getter, capture_io, api_name):
    def _monitor(f):
        def monitored(*args, **kwargs):
            # Create a UUID to uniquely identify this run from the SDK's point of view
            current_sdk_run_uuid = str(uuid.uuid4())

            # Capture STDOUT/STDERR before they're modified
            old_out, old_err = sys.stdout, sys.stderr
 
            # Buffers to which to redirect output so we can capture it
            out = [IOBuffer(), IOBuffer()]

            logger = get_logger(model_name, current_sdk_run_uuid, out[0])

            if capture_io:
                # Redirect STDOUT/STDERR to buffers
                sys.stdout, sys.stderr = out

            if not hasattr(f, 'callcount'):
                f.callcount = 0
            if f.callcount >= 1:
                raise Exception(
                    "Hyperdash does not support recursive functions!")
            else:
                f.callcount += 1
            try:
                server_manager = ServerManagerHTTP(api_key_getter, logger, api_name)
                hd_client = HDClient(logger, server_manager, current_sdk_run_uuid)
                code_runner = CodeRunner(f, hd_client, logger, *args, **kwargs)
                hyper_dash = HyperDash(
                    model_name,
                    current_sdk_run_uuid,
                    server_manager,
                    out,
                    (old_out, old_err,),
                    logger,
                    code_runner,
                )
                return_val = hyper_dash.run()
                f.callcount -= 1
                return return_val
            # Prevent uncaught exceptions from silently being swallowed
            except Exception:
                raise
            finally:
                # Cleanup
                sys.stdout, sys.stderr = old_out, old_err
        return monitored
    return _monitor
