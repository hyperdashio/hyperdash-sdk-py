import datetime
import logging

def get_logger(model_name, current_sdk_run_uuid, stdout_buffer):
   # Include the model_name/UUID in the logger name to make
    # sure that its always distinct, even if multiple runs
    # of the same model are happening at the same time in
    # different threads
    logger = logging.getLogger(
        "{}-{}".format(model_name, current_sdk_run_uuid))
    # Remove any existing log handlers so it doesn't double log
    logger.handlers = []
    # Don't propagate to the root logger
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(stdout_buffer))
    return logger


def human_readable_duration(start_time, end_time):
    return str(datetime.timedelta(seconds=(end_time-start_time).seconds))