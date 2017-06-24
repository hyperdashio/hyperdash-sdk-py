# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
import time

from code_runner import CodeRunner
from hyper_dash import HyperDash
from io_buffer import IOBuffer
from server_manager import ServerManager


# TODO: We should probably spawn a separate process instead of using a thread
# so that it is easier to kill jobs, but that makes capturing STDOUT trickier
# so we use threads for now.

# TODO: I think StringIO buffers don't handle unicode properly. Investigate.


def monitor(job_name, api_key_getter=None):
    server_manager = ServerManager(custom_api_key_getter=api_key_getter)

    def _monitor(f):
        # Buffers to which to redirect output so we can capture it
        out = [IOBuffer(), IOBuffer()]
        logging.basicConfig(stream=out[0], level=logging.INFO)

        # Capture STDOUT/STDERR before they're modified
        old_out, old_err = sys.stdout, sys.stderr

        # Redirect STDOUT/STDERR to buffers
        sys.stdout, sys.stderr = out

        def monitored(*args, **kwargs):
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
                    code_runner,
                    server_manager,
                    out,
                    (old_out, old_err,),
                    custom_api_key_getter=api_key_getter,
                )
                hyper_dash.run()
                print("User code run successfully. Waiting for further instructions from server...")
            # Prevent uncaught exceptions from silently being swallowed
            except Exception:
                raise
            finally:
                # Cleanup
                sys.stdout, sys.stderr = old_out, old_err
        return monitored
    return _monitor


# Notice that all the user has to do is add the @monitor decorator
# with an appropriate API key, and optionally add the smart_ml
# argument to their function signature (if they want to use features
# other than viewing print statements and starting/stopping their jobs.)
@monitor(job_name="the_donald")
def main(model_name, epoch_duration, hyperdash=None):
    print("Training model: {}".format(model_name))
    print("Retrieving model parameters from remote server...")
    time.sleep(2)

    num_epochs = hyperdash.get_param("num_epochs", 5)
    print("Retrieved {} num_epochs from server.".format(num_epochs))
    for i in range(num_epochs):
        print("Beginning epoch {}".format(i))
        time.sleep(epoch_duration)
        print("Epoch {} completed. Accuracy: {}%".format(i, 25+i*25))
        if i == 0:
            print("Sample output: 'Murica'")
        if i == 1:
            print("Sample output: 'Make America Great Again!'")
        if i == 2:
            print("And I told them, we have the most tremendous country. America is gonna be yuge again.")

main("trump_bot", 5)
