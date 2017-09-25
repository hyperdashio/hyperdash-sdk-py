from .monitor import monitor
from .jupyter import IPythonMagicsWrapper as IPythonMagicsWrapper
from .experiment import Experiment

# No-op just to make import nicer
def monitor_cell():
  pass

try:
  ip = get_ipython()
  ip.register_magics(IPythonMagicsWrapper)
except NameError:
  pass
