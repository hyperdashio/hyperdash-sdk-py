# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import sys
import time

from collections import deque
from traceback import format_exc

from requests.exceptions import BaseHTTPError
from requests import Request
from requests import Session as HTTPSession

from .constants import API_KEY_NAME
from .constants import AUTH_KEY_NAME
from .constants import CACHE_API_KEY_FOR_SECONDS
from .constants import get_hyperdash_json_paths
from .constants import get_http_url
from .constants import get_hyperdash_version
from .constants import VERSION_KEY_NAME
from .sdk_message import create_heartbeat_message


# Python 2/3 compatibility
__metaclass__ = type


class ServerManagerBase():
    # TODO: Check type
    def put_buf(self, m):
        self.out_buf.append(m)

    def tick(self, sdk_run_uuid):
        raise NotImplementedError()

    def send_message(self, message, raise_exceptions=True, **kwargs):
        raise NotImplementedError()

    def get_api_key(self):
        cur_time = time.time()

        # Use cached API key if available
        if self.fetched_api_key_at and cur_time - self.fetched_api_key_at < CACHE_API_KEY_FOR_SECONDS:
            return self.api_key

        # Set this now regardless of the outcome to make sure it runs
        self.fetched_api_key_at = cur_time

        # If they provided a custom function, just use that
        if self.custom_api_key_getter:
            api_key = self.custom_api_key_getter()
            is_py3 = sys.version_info[0] == 3
            if is_py3:
                string_types = (str,)
            else:
                string_types = (basestring,)
            if not isinstance(api_key, string_types):
                self.log_error_once(
                    "custom_api_key_getter returned non-string value")
            self.api_key = api_key
            return api_key

        # Otherwise check for hyperdash.json and HYPERDASH_API_KEY env variable
        from_file = self.get_api_key_from_file()
        from_env = self.get_api_key_from_env()

        if not (from_file or from_env):
            self.log_error_once(
                "Unable to detect API key in hyperdash.json or HYPERDASH_API_KEY environment variable")

        if from_file and from_env:
            self.log_error_once(
                "Found API key in hyperdash.json AND HYPERDASH_API_KEY environment variable. Environment variable will take precedence.")

        self.api_key = from_env or from_file
        return self.api_key

    def get_api_key_from_file(self):
        parsed = None
        for path in get_hyperdash_json_paths():
            try:
                with open(path, "r") as f:
                    try:
                        parsed = json.load(f)
                    except ValueError:
                        self.log_error_once("hyperdash.json is not valid JSON")
                        return None
            except IOError:
                continue

        return parsed.get('api_key') if parsed else None

    def get_api_key_from_env(self):
        return os.environ.get("HYPERDASH_API_KEY")

    def log_error_once(self, message):
        if message in self.logged_errors:
            return
        self.logger.error(message)
        self.logged_errors.add(message)

    def should_send_heartbeat(self):
        return (
            len(self.out_buf) == 0 and
            self.last_message_sent_at and
            # TODO: Constantize/config
            time.time() - self.last_message_sent_at >= 5
        )

    def cleanup(self, sdk_run_uuid):
        raise NotImplementedError()

    def __init__(self, custom_api_key_getter, parent_logger, api_name):
        self.out_buf = deque()
        self.in_buf = deque()
        self.logger = parent_logger.getChild(__name__)
        self.custom_api_key_getter = custom_api_key_getter
        self.logged_errors = set()
        self.unauthorized = False
        self.api_key = None
        self.fetched_api_key_at = None
        self.last_message_sent_at = None
        self.version = get_hyperdash_version()
        self.api_name = api_name


class ServerManagerHTTP(ServerManagerBase):

    def tick(self, sdk_run_uuid):
        if self.unauthorized:
            return False

        # If there are no messages to be sent, check if we
        # need to send a heartbeat
        if self.should_send_heartbeat():
            try:
                self.send_message(create_heartbeat_message(sdk_run_uuid))
            except BaseHTTPError as e:
                self.log_error_once(
                    "Unable to send heartbeat due to connection issues: {}".format(
                        e),
                )
                return False
            except Exception as e:
                self.logger.debug(e)
                self.log_error_once("Unable to send heartbeat message")
                return False

        # TODO: Move while loop out of tick function
        while True:
            try:
                message = self.out_buf.popleft()
            # Empty
            except IndexError:
                # Clean exit
                return True

            sent_successfully = False
            is_poison_pill = False
            try:
                res = self.send_message(message)
                if res.status_code != 200:
                    # TODO: Server should return better error message
                    err_code = res.json()["code"]
                    if err_code == "api_key_requred":
                        self.unauthorized = True
                    self.log_error_once(
                        "Error from Hyperdash server: {}".format(err_code))
                    # Status code 400 indicates there is something malformed
                    # about the message. Mark it as poison so we don't keep
                    # retrying.
                    if res.status_code == 400:
                        is_poison_pill = True
                else:
                    sent_successfully = True
            except BaseHTTPError as e:
                self.log_error_once(
                    "Unable to send message due to connection issues: {}".format(
                        e),
                )
            except Exception as e:
                self.logger.debug(format_exc())
                self.log_error_once(
                    "Unable to communicate with Hyperdash servers")

            if sent_successfully is not True and not is_poison_pill:
                # Re-enque so message is not lost
                self.out_buf.appendleft(message)
                return False

    def send_message(self, message, raise_exceptions=True, timeout_seconds=5):
        try:
            return self.s.post(
                get_http_url(),
                json=json.loads(message),
                headers={
                    AUTH_KEY_NAME: self.get_api_key(),
                    VERSION_KEY_NAME: self.version,
                    API_KEY_NAME: self.api_name,
                },
                timeout=timeout_seconds,
            )
        except Exception:
            if raise_exceptions:
                raise
        finally:
            self.last_message_sent_at = time.time()

    def cleanup(self, sdk_run_uuid):
        # Try to flush any remaining messages
        return self.tick(sdk_run_uuid)

    def __init__(self, custom_api_key_getter, parent_logger, api_name):
        ServerManagerBase.__init__(self, custom_api_key_getter, parent_logger, api_name)
        # TODO: Keep alive
        # TODO: Timeout
        self.s = HTTPSession()
