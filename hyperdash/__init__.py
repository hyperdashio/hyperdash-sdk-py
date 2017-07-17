from .sdk import monitor
from .jupyter import IPythonMagicsWrapper as IPythonMagicsWrapper

# No-op just to make import nicer
def monitor_cell():
  pass

try:
  ip = get_ipython()
  ip.register_magics(IPythonMagicsWrapper)
except NameError:
  pass
