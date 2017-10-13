from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import uuid
import threading
from threading import Lock

from datetime import datetime

from six.moves.queue import Queue

from .client import HDClient
from .constants import API_NAME_EXPERIMENT
from .monitor import monitor
from .io_buffer import IOBuffer
from .server_manager import ServerManagerHTTP
from .hyper_dash import HyperDash
from .utils import get_logger

# Python 2/3 compatibility
__metaclass__ = type

"""
    No-op class for reusing CodeRunner architecture
"""

class ExperimentRunner:
    def __init__(
        self,
        done=False,
        exit_cleanly=True,
    ):
        self.done = done
        self.lock = Lock()
        self.exit_cleanly = exit_cleanly
        self.start_time = None
        self.end_time = None

    def is_done(self):
        with self.lock:
            return self.exit_cleanly, self.done

    def get_return_val(self):
        with self.lock:
            return None

    def get_exception(self):
        with self.lock:
            return None
        
    def should_run_as_thread(self):
        return False

    def get_start_and_end_time(self):
        return self.start_time, self.end_time

    def _set_start_time(self, start_time):
        self.start_time = start_time

    def _set_end_time(self, end_time):
        self.end_time = end_time

class Experiment:
    """Experiment records hyperparameters and metrics. The recorded values
    are sent to the Hyperdash server.

    Example:
      exp = Experiment("MNIST")
      exp.param("batch size", 32)
    """
    def __init__(
        self,
        model_name,
        api_key_getter=None,
        capture_io=True,
    ):
        """Initialize the HyperDash class.

        args:
            1) model_name: Name of the model. Experiment number will autoincrement. 
            2) capture_io: Should save stdout/stderror to log file and upload it to Hyperdash.
        """
        self.model_name = model_name
        self._experiment_runner = ExperimentRunner()
        self.lock = Lock()

        # Create a UUID to uniquely identify this run from the SDK's point of view
        current_sdk_run_uuid = str(uuid.uuid4())

        # Capture STDOUT/STDERR before they're modified
        self._old_out, self._old_err = sys.stdout, sys.stderr

        # Buffers to which to redirect output so we can capture it
        out = [IOBuffer(), IOBuffer()]

        self._logger = get_logger(model_name, current_sdk_run_uuid, out[0])

        if capture_io:
            # Redirect STDOUT/STDERR to buffers
            sys.stdout, sys.stderr = out

        server_manager = ServerManagerHTTP(api_key_getter, self._logger, API_NAME_EXPERIMENT)
        self._hd_client = HDClient(self._logger, server_manager, current_sdk_run_uuid)
        self._hd = HyperDash(
            model_name,
            current_sdk_run_uuid,
            server_manager,
            out,
            (self._old_out, self._old_err,),
            self._logger,
            self._experiment_runner,
        )
        # Channel to update once experiment has finished running
        # Syncs with the seperate hyperdash messaging loop thread
        self.done_chan = Queue()
        def run():
            self._experiment_runner._set_start_time(datetime.now())
            self._hd.run()
            self._experiment_runner._set_end_time(datetime.now())
            self.done_chan.put(True)
        exp_thread = threading.Thread(target=run)
        exp_thread.daemon = True
        exp_thread.start()
        self._ended = False

    def metric(self, name, value, log=True):
        if self._ended:
            self._logger.warn("Cannot send metric {}, experiment ended. Please start a new experiment.".format(name))
            return
        return self._hd_client.metric(name, value, log)

    def param(self, name, value, log=True):
        if self._ended:
            self._logger.warn("Cannot send param {}, experiment ended. Please start a new experiment.".format(name))
            return
        return self._hd_client.param(name, value, log)

    def iter(self, n, log=True):
        if self._ended:
            self._logger.warn("Cannot iterate, experiment ended. Please start a new experiment.")
            return
        return self._hd_client.iter(n,log)

    def end(self):
        if self._ended:
            return

        self._ended = True
        with self.lock:
            sys.stdout, sys.stderr = self._old_out, self._old_err
            self._experiment_runner.exit_cleanly = True
            self._experiment_runner.done = True
            # Makes sure the experiment runner has cleaned up fully 
    
        self.done_chan.get(block=True, timeout=None)
    """
    For selective logging while capture_io is disabled
    
    Main use case is if you output large amounts of text to STDOUT
    but only want a subset saved to logs
    """
    def log(self, string):
        self._logger.info(string)
