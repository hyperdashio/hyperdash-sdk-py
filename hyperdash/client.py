from .sdk_message import create_metric_message
from .sdk_message import create_param_message
import numbers
import six
import json


class HDClient:
    def __init__(self, logger, server_manager, sdk_run_uuid):
        self.logger = logger
        self.server_manager = server_manager
        self.sdk_run_uuid = sdk_run_uuid
        # Keeps track of which parameters have been seen before
        # so we can prevent duplicates
        self.seen_params = set()
        # Keeps track of how many iterators have been created
        # so we can give them distinct names
        self.iter_num = 0

    def metric(self, name, value, log=True):
        """Emit a datapoint for a named timeseries.

        Optional log parameter controls whether the metric is
        logged / printed to STDOUT.
        """
        return self._metric(name, value, log, False)

    def _metric(self, name, value, log=True, is_internal=False):
        assert isinstance(value, numbers.Real), "value must be a real number."
        assert isinstance(name, six.string_types)
        assert value is not None and name is not None, "value and name must not be None."

        message = create_metric_message(
            self.sdk_run_uuid, name, value, is_internal)
        self.server_manager.put_buf(message)
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
        json.dumps(val)
        assert name not in self.seen_params, "hyperparameters should be unique and not reused"

        params = {}
        params[name] = val
        message = create_param_message(self.sdk_run_uuid, params, is_internal)
        self.server_manager.put_buf(message)
        self.seen_params.add(name)
        if log:
            self.logger.info("{{ {}: {} }}".format(name, val))
        return val

    def iter(self, n):
        """Returns an iterator with the specified number of iterations.

        The iter method automatically associated the number of iterations
        with the experiment, as well as emits timeseries data for each
        iteration so that progress can be monitored.
        """
        i = 0
        # Capture the existing iterator number
        iter_num = self.iter_num
        # Increment the iterator number for subsequent calls
        self.iter_num += 1
        self._param("hd_iter_{}_epochs".format(iter_num),
                    n, log=False, is_internal=True)
        while i < n:
            self._metric("hd_iter_{}".format(iter_num),
                         i, log=False, is_internal=True)
            yield i
            i += 1
