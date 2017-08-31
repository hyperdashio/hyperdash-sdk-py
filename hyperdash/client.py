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

    def metric(self, name, value):
        assert isinstance(value, numbers.Real), 'value must be a real number.'
        assert isinstance(name, six.string_types)
        assert value is not None and name is not None, 'value and name must not be None.'

        message = create_metric_message(self.sdk_run_uuid, name, value)
        self.server_manager.put_buf(message)
        self.logger.info("| {0}: {1:10f} |".format(name, value))

    def param(self, name, val):
        assert isinstance(name, six.string_types), 'name must be a string.'
        # Make sure its JSON serializable
        json.dumps(val)

        params = {}
        params[name] = val
        message = create_param_message(self.sdk_run_uuid, params)
        self.server_manager.put_buf(message)
        self.logger.info("{{ {}: {} }}".format(name, val))
        return val
