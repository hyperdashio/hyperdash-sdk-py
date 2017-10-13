import time

import numbers
import six
import json

from .sdk_message import create_metric_message
from .sdk_message import create_param_message


class HDClient:
    def __init__(self, logger, server_manager, sdk_run_uuid):
        self.logger = logger
        self._server_manager = server_manager
        self._sdk_run_uuid = sdk_run_uuid
        # Keeps track of which parameters have been seen before
        # so we can prevent duplicates
        self._seen_params = set()
        # Keeps track of how many iterators have been created
        # so we can give them distinct names
        self._iter_num = 0
        # Keep track of the last time we saw a metric so we can
        # limit how often the are emitted
        self._last_seen_metrics = {}

    def metric(self, name, value, log=True):
        """Emit a datapoint for a named timeseries.

        Optional log parameter controls whether the metric is
        logged / printed to STDOUT.
        """
        return self._metric(name, value, log, False)

    def _metric(self, name, value, log=True, is_internal=False, sample_frequency_per_second=1):
        assert isinstance(value, numbers.Real), "value must be a real number."
        assert isinstance(name, six.string_types)
        assert isinstance(sample_frequency_per_second, numbers.Real), "sample_frequency_per_second must be a real number."
        assert value is not None and name is not None and sample_frequency_per_second is not None, "value and name and sample_frequency_per_second must not be None."
        # We've already determined its a real number, but some objects that satisfy the real number
        # constraint (like numpy numbers) are not JSON serializable unless converted.
        value = float(value)

        current_time = time.time()
        last_seen_at = self._last_seen_metrics.get(name, None)
        if last_seen_at and (current_time - last_seen_at < (1.0/float(sample_frequency_per_second))):
            # Not enough time has elapsed since the last time this metric was emitted
            return

        message = create_metric_message(
            self._sdk_run_uuid, name, value, is_internal)
        self._server_manager.put_buf(message)
        self._last_seen_metrics[name] = current_time
        if log:
            self.logger.info("| {0}: {1:10f} |".format(name, value))

    def param(self, name, val, log=True):
        """Associate a hyperparameter with the given experiment.

        Optional log parameter controls whether the hyperparameter
        is logged / printed to STDOUT.
        """
        return self._param(name, val, log, False)

    def _param(self, name, val, log=True, is_internal=False):
        assert isinstance(name, six.string_types), "name must be a string."
        # Make sure its JSON serializable
        try:
            json.dumps(val)
        except TypeError:
            # If its not, see if its a number
            if isinstance(val, numbers.Real):
                val = float(val)
            else:
            # Otherwise, just convert it to a string
                val = str(val)
        assert name not in self._seen_params, "hyperparameters should be unique and not reused"

        params = {}
        params[name] = val
        message = create_param_message(self._sdk_run_uuid, params, is_internal)
        self._server_manager.put_buf(message)
        self._seen_params.add(name)
        if log:
            self.logger.info("{{ {}: {} }}".format(name, val))
        return val

    def iter(self, n, log=True):
        """Returns an iterator with the specified number of iterations.

        The iter method automatically associated the number of iterations
        with the experiment, as well as emits timeseries data for each
        iteration so that progress can be monitored.
        """
        i = 0
        # Capture the existing iterator number
        iter_num = self._iter_num
        # Increment the iterator number for subsequent calls
        self._iter_num += 1
        self._param("hd_iter_{}_epochs".format(iter_num),
                    n, log=False, is_internal=True)
        while i < n:
            if log:
                self.logger.info("| Iteration {} of {} |".format(i, n - 1))
            self._metric("hd_iter_{}".format(iter_num),
                         i, log=False, is_internal=True)
            yield i
            i += 1

    def end(self):
        self.logger.warning("end() call is unneccessary while using decorator syntax.")