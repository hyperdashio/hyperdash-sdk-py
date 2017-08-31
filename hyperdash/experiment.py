from .client import HDClient

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
        log_records=True,
    ):
        """Initialize the HyperDash class.

        args:
            1) model_name: Name of the model. Experiment number will autoincrement. 
            2) log_records: Should print pretty formatted values of hyperparameters and metrics.
        """
      self.model_name = model_name
      self.log_records = log_records
      self.client = HDClient()
    