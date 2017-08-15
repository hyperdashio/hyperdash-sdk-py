from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import os
import requests
import socket
import time

handle_request_cache = dict()


class MockServerRequestHandler(BaseHTTPRequestHandler):

    def handle_request(self, method, path):
        handle = handle_request_cache.get((method, path))
        if not handle:
            raise Exception(
                "Mock server called with unknown request {} {}".format(method, path))

        handle(self)

    def do_GET(self): self.handle_request("GET", self.path)

    def do_POST(self): self.handle_request("POST", self.path)

    # Turn off HTTP logging so they don't interfere with STDOUT for our tests
    def log_message(*args, **kwargs):
        pass


def init_mock_server():
    # Get port
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()

    # Start server
    mock_server = HTTPServer(('localhost', port), MockServerRequestHandler)
    mock_server_thread = Thread(target=mock_server.serve_forever)
    mock_server_thread.setDaemon(True)
    mock_server_thread.start()

    # Override production server
    server = 'http://localhost:{}'.format(port)
    os.environ['HYPERDASH_SERVER'] = server

    return handle_request_cache
