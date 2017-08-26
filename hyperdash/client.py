from .sdk_message import create_metric_message
import numbers
import types

class HDClient:
    def __init__(self, logger, server_manager, sdk_run_uuid):
        self.logger = logger
        self.server_manager = server_manager
        self.sdk_run_uuid = sdk_run_uuid

    def metric(self, value, name):
        assert isinstance(value, numbers.Real), 'value must be a real number.'
        assert isinstance(name, types.StringType)
        assert value is not None and name is not None, 'value and name must not be None.'

        message = self.server_manager.create_metric_message(self.sdk_run_uuid, value, name)
        self.server_manager.put_buf(message)