from .sdk import monitor

def ipython_required_decorator(_):
  def decorated():
    raise Exception("IPython is required to use monitor_cell function")
  return decorated

# Handle situation where IPython is not in the local environment OR
# it is available, but we're not running in the context of an IPython
# notebook.
try:
  from IPython.core.magic import register_cell_magic
except ImportError:
  register_cell_magic = ipython_required_decorator
try:
  get_ipython
except NameError:
  register_cell_magic = ipython_required_decorator


@register_cell_magic
def monitor_cell(line, cell):
    if line is None or line == "":
        return "ERROR: Please provide a valid model name. Ex. %%hyperdash dogs vs. cats"

    @monitor(line, use_http=True)
    def wrapped():
        exec(cell) in globals(), locals()
    wrapped()
