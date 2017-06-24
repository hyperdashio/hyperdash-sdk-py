from io import StringIO


class IOBuffer:
    def __init__(self):
        self.buf = StringIO()

    # Wrap the write method so the buffer can handle inputs other than strings
    # Otherwise it would fail with calls like: print(1) or print(<SOME_OBJECT>)
    def write(self, input):
        uni = unicode(input)
        self.buf.write(uni)

    def getvalue(self):
        return self.buf.getvalue()

    def close(self):
        self.buf.close()
