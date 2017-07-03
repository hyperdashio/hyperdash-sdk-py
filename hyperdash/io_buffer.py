from io import StringIO
from six import text_type


def noop():
    pass


class IOBuffer:
    def __init__(self, on_flush=noop):
        self.buf = StringIO()
        self.on_flush = on_flush

    # Wrap the write method so the buffer can handle inputs other than strings
    # Otherwise it would fail with calls like: print(1) or print(<SOME_OBJECT>)
    def write(self, input):
        uni = text_type(input)
        self.buf.write(uni)

    def getvalue(self):
        return self.buf.getvalue()

    def close(self):
        self.buf.close()

    def flush(self):
        self.on_flush()

    def set_on_flush(self, on_flush):
        self.on_flush = on_flush
