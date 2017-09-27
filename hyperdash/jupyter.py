from six import PY2

from .constants import API_NAME_JUPYTER
from .monitor import _monitor

# Handle situation where IPython is not in the local environment OR
# it is available, but we're not running in the context of an IPython
# notebook.
try:
    from IPython.core.magic import cell_magic
    from IPython.core.magic import magics_class
    from IPython.core.magic import Magics
    from IPython.core.magic import needs_local_scope

    # Syntax for exec changes between Python2/3 (in Python2 its a statement
    # and in Python3 its a function) so we have to wrap it like this to
    # prevent pre-runtime syntax errors
    if PY2:
        from .jupyter_2_exec import wrapped_exec
    else:
        from .jupyter_3_exec import wrapped_exec

    @magics_class
    class IPythonMagicsWrapper(Magics):
        @needs_local_scope
        @cell_magic
        def monitor_cell(self, line, cell, local_ns=None):
            if line is None or line == "":
                return "ERROR: Please provide a valid model name. Ex. %%monitor_cell dogs vs. cats"

            @_monitor(line, api_key_getter=None, capture_io=True, api_name=API_NAME_JUPYTER)
            def wrapped():
                wrapped_exec(cell, self.shell.user_ns, local_ns)
            wrapped()

except ImportError:
    class IPythonMagicsWrapper:
        pass
