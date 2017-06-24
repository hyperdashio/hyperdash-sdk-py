# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging
import os
import sys

from collections import deque

from ws4py.client.threadedclient import WebSocketClient
from ws4py.exc import HandshakeError


# Python 2/3 compatibility
__metaclass__ = type


class ServerManager(WebSocketClient):

    def opened(self):
        pass

    def closed(self, code, reason=None):
        print("Closed down", code, reason)
        self.active = False

    def received_message(self, m):
        self.in_buf.append(m)

    # TODO: Check type
    def put_buf(self, m):
        self.out_buf.append(m)

    def tick(self):
        if not self.active:
            success = self.reconnect()
            # Skip this tick
            if not success:
                return

        # TODO: Max messages per tick?
        while True:
            try:
                message = self.out_buf.popleft()
            # Empty
            except IndexError:
                return

            try:
                self.send(message)
            # Poison-pill, drop it
            except ValueError:
                self.logger.debug("Invalid websocket message")
                continue
            except Exception:
                # Assume we've been disconnected
                self.active = False
                # Re-enque so message is not lost
                self.out_buf.appendleft(message)
                self.logger.debug("Unable to send websocket message")
                break

    def reconnect(self):
        api_key = self.get_api_key()
        if not api_key:
            return False

        try:
            super(ServerManager, self).__init__(
                "ws://127.0.0.1:4000/api/websocket",
                protocols=["http-only", "chat"],
                headers=[("x-hyperdash-auth", api_key,)],
            )
            self.connect()
            self.active = True
        except HandshakeError as h:
            if '401' in h.msg:
                self.log_error_once("api key: {} is invalid".format(api_key))
            else:
                self.log_error_once("Handshake error: {}".format(h.msg))
            return False
        except Exception as e:
            self.log_error_once("Unable to connect to hyperdash server")
            return False

        return True

    def get_api_key(self):
        # If they provided a custom function, just use that
        if self.custom_api_key_getter:
            api_key = self.custom_api_key_getter()
            is_py3 = sys.version_info[0] == 3
            if is_py3:
                string_types = (str,)
            else:
                string_types = (basestring,)
            if not isinstance(api_key, string_types):
                self.log_error_once("custom_api_key_getter returned non-string value")
            return api_key

        # Otherwise check for hyperdash.json and HYPERDASH_API_KEY env variable
        from_file = self.get_api_key_from_file()
        from_env = self.get_api_key_from_env()

        if not (from_file or from_env):
            self.log_error_once("Unable to detect API key in hyperdash.json or HYPERDASH_API_KEY environment variable")

        if from_file and from_env:
            self.log_error_once("Found API key in hyperdash.json AND HYPERDASH_API_KEY environment variable. Please only use one.")

        return from_file or from_env

    def get_api_key_from_file(self):
        main = sys.modules["__main__"]
        if not hasattr(main, "__file__"):
            return None

        main_file_path = os.path.abspath(main.__file__)
        root_folder = os.path.dirname(main_file_path)
        hyperdash_file_path = os.path.join(root_folder, "hyperdash.json")

        try:
            with open(hyperdash_file_path, "r") as f:
                try:
                    parsed = json.load(f)
                except ValueError:
                    self.log_error_once("hyperdash.json is not valid JSON")
                    return None
        except IOError:
            self.logger.debug("hyperdash.json not found")
            return None

        return parsed.get("api_key")

    def get_api_key_from_env(self):
        return os.environ.get("HYPERDASH_API_KEY")

    def log_error_once(self, message):
        if message in self.logged_errors:
            return
        self.logger.error(message)
        self.logged_errors.add(message)

    def cleanup(self):
        if not self.active:
            return

        self.close()
        self.active = False

    def __init__(self, custom_api_key_getter):
        self.out_buf = deque()
        self.in_buf = deque()
        self.logger = logging.getLogger("hyperdash.{}".format(__name__))
        self.active = False
        self.custom_api_key_getter = custom_api_key_getter
        self.logged_errors = set()
