from .sdk import monitor


# Handle situation where IPython is not in the local environment OR
# it is available, but we're not running in the context of an IPython
# notebook.
try:
  from IPython.core.magic import cell_magic
  from IPython.core.magic import magics_class
  from IPython.core.magic import Magics
  from IPython.core.magic import needs_local_scope

  @magics_class
  class IPythonMagicsWrapper(Magics):
    @needs_local_scope
    @cell_magic
    def monitor_cell(self, line, cell, local_ns=None):
      if line is None or line == "":
        return "ERROR: Please provide a valid model name. Ex. %%monitor_cell dogs vs. cats"
      
      @monitor(line)
      def wrapped():
        exec cell in self.shell.user_ns, local_ns
      wrapped()

except ImportError:
  class IPythonMagicsWrapper:
    pass
