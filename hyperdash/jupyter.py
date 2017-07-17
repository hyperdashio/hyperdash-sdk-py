from .sdk import monitor


# Handle situation where IPython is not in the local environment OR
# it is available, but we're not running in the context of an IPython
# notebook.
try:
  from IPython.core.magic import cell_magic
  from IPython.core.magic import magics_class
  from IPython.core.magic import Magics

  @magics_class
  class IPythonMagicsWrapper(Magics):
    @cell_magic
    def monitor_cell(self, line, cell):
      if line is None or line == "":
        return "ERROR: Please provide a valid model name. Ex. %%monitor_cell dogs vs. cats"
      
      @monitor(line, use_http=True)
      def wrapped():
        ns = {}
        exec(cell, self.shell.user_ns, ns)
      wrapped()

except ImportError:
  class IPythonMagicsWrapper:
    pass
