from hyperdash.io_buffer import IOBuffer


class TestBuffer(object):
    """TestBuffer contains tests for the IOBuffer class."""
    def test_buffer_has_atty_method(self):
        """Verify IOBuffer has an atty() method."""
        buf = IOBuffer()
        assert buf.isatty() is True