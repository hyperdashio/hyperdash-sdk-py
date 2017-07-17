# Python 2/3 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging
import os
import sys
import time

from collections import deque
from traceback import format_exc

from autobahn.twisted.wamp import Session as WAMPSession
from autobahn.twisted.wamp import ApplicationRunner
from autobahn.wamp.exception import ApplicationError
from autobahn.wamp.types import CallOptions

from requests.exceptions import BaseHTTPError
from requests import Request
from requests import Session as HTTPSession

from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import returnValue

from .constants import AUTH_KEY_NAME
from .constants import CACHE_API_KEY_FOR_SECONDS
from .constants import get_hyperdash_json_paths
from .constants import get_http_url
from .constants import get_wamp_url
from .constants import WAMP_REALM
from .sdk_message import create_heartbeat_message


# Python 2/3 compatibility
__metaclass__ = type


class Borg:
    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state


class ServerManagerBase(Borg):
    """
    The ServerManager class inherits from Borg (to make it a singleton)
    and from Session to use the WAMP protocol.

    We want this class to behave like a Singleton because the interface
    exposed by the Autobahn WAMP library accepts a class and instantiates
    it, preventing us from doing any initialization. Making the class a
    singleton allows us to instantiate it and configure it before the
    library does.

    We also define a custom_init() function instead of using __init__() to
    setup the class's state. This is because the auto_reconnect feature of
    the Autobahn library internally calls __init__. Thus, if we setup our
    state in __init__ we would lose all pending incoming/outgoing messages
    everytime we were disconnected.
    """
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
                self.log_error_once("custom_api_key_getter returned non-string value")
            return api_key

        # Otherwise check for hyperdash.json and HYPERDASH_API_KEY env variable
        from_file = self.get_api_key_from_file()
        from_env = self.get_api_key_from_env()

        if not (from_file or from_env):
            self.log_error_once("Unable to detect API key in hyperdash.json or HYPERDASH_API_KEY environment variable")

        if from_file and from_env:
            self.log_error_once("Found API key in hyperdash.json AND HYPERDASH_API_KEY environment variable. Hyperdash.json will take precedence.")

        self.api_key = from_file or from_env
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
        return  (
            len(self.out_buf) == 0 and
            self.last_message_sent_at and
            # TODO: Constantize/config
            time.time() - self.last_message_sent_at >= 5
        )

    def cleanup(self, sdk_run_uuid):
        raise NotImplementedError()

    def custom_init(self, custom_api_key_getter):
        self.out_buf = deque()
        self.in_buf = deque()
        self.logger = logging.getLogger("hyperdash.{}".format(__name__))
        self.custom_api_key_getter = custom_api_key_getter
        self.logged_errors = set()
        self.unauthorized = False
        self.api_key = None
        self.fetched_api_key_at = None
        self.last_message_sent_at = None

    def __init__(self, *args, **kwargs):
        Borg.__init__(self)


class ServerManagerHTTP(ServerManagerBase):

    def tick(self, sdk_run_uuid):
        if self.unauthorized:
            returnValue(False)

        # If there are no messages to be sent, check if we
        # need to send a heartbeat
        if self.should_send_heartbeat():
            try:
                self.send_message(create_heartbeat_message(sdk_run_uuid))
            except BaseHTTPError as e:
                self.log_error_once(
                    "Unable to send heartbeat due to connection issues: {}".format(e),
                )
                return False
            except Exception as e:
                self.logger.debug(e)
                self.log_error_once("Unable to send heartbeat message")
                return False

        # TODO: Max messages per tick?
        # TODO: Message batching
        while True:
            try:
                message = self.out_buf.popleft()
            # Empty
            except IndexError:
                # Clean exit
                return True

            sent_successfully = False
            try:
                res = self.send_message(message)
                if res.status_code != 200:
                    # TODO: Server should return better error message
                    err_code = res.json()["code"]
                    if err_code == "api_key_requred":
                        self.unauthorized = True
                    self.log_error_once("Error from Hyperdash server: {}".format(err_code))
                else:
                    sent_successfully = True
            except BaseHTTPError as e:
                self.log_error_once(
                    "Unable to send message due to connection issues: {}".format(e),
                )
            except Exception as e:
                self.logger.debug(format_exc())
                self.log_error_once("Unable to communicate with Hyperdash servers")

            if sent_successfully is not True:
                # Re-enque so message is not lost
                self.out_buf.appendleft(message)
                return False

    def send_message(self, message, raise_exceptions=True):
        try:
            return self.s.post(
                get_http_url(),
                json=json.loads(message),
                headers={AUTH_KEY_NAME: self.get_api_key()},
            )
        finally:
            self.last_message_sent_at = time.time()

    def cleanup(self, sdk_run_uuid):
        # Try and flush any remaining messages
        return self.tick(sdk_run_uuid)

    def custom_init(self, custom_api_key_getter):
        ServerManagerBase.custom_init(self, custom_api_key_getter)
        # TODO: Keep alive
        # TODO: Timeout
        self.s = HTTPSession()


class ServerManagerWAMP(ServerManagerBase, WAMPSession):
    def onJoin(self, *args, **kwargs):
        self.logger.debug("Realm joined")
        self.unauthorized = False

    def onClose(self, wasClean, code=None, reason=None):
        if reason and "401" in reason:
            self.unauthorized = True
            # Prevent auto-reconnect from trying forever
            self.application_runner.stop()

            api_key = self.get_api_key()
            self.log_error_once("Invalid API key: {}".format(api_key))
        elif not wasClean:
            self.log_error_once(
                "Connection to Hyperdash servers terminated: {}".format(reason),
            )

    def received_message(self, m):
        self.in_buf.append(m)

    @inlineCallbacks
    def tick(self, sdk_run_uuid):
        if self.unauthorized:
            returnValue(False)

        # If there are no messages to be sent, check if we
        # need to send a heartbeat
        if self.should_send_heartbeat():
            try:
                yield self.send_message(create_heartbeat_message(sdk_run_uuid))
            except ApplicationError as e:
                self.log_error_once(
                    "Unable to send heartbeat: {}".format(e.error_message()),
                )
            except Exception as e:
                self.log_error_once("Unable to send heartbeat message")

        # TODO: Max messages per tick?
        # TODO: Message batching
        while True:
            try:
                message = self.out_buf.popleft()
            # Empty
            except IndexError:
                # Clean exit
                returnValue(True)

            try:
                yield self.send_message(message)
            # Poison-pill, drop it
            except ValueError:
                self.logger.debug("Invalid websocket message")
                continue
            except ApplicationError as e:
                if "api_key_required" in e.error_message():
                    self.unauthorized = True
                    # Prevent auto-reconnect from trying forever
                    self.application_runner.stop()
                    api_key = self.get_api_key()
                    self.log_error_once("Invalid API key: {}".format(api_key))
                else:
                    self.log_error_once(
                        "Error communicating with Hyperdash servers: {}".format(
                            e.error_message(),
                        ),
                    )

                # Re-enque so message is not lost
                self.out_buf.appendleft(message)
                returnValue(False)
                return
            except Exception:
                # Re-enque so message is not lost
                self.out_buf.appendleft(message)
                self.log_error_once("Error communicating with Hyperdash servers...")
                self.logger.debug("Error sending WAMP message")
                # Exited with pending messages
                returnValue(False)

    @inlineCallbacks
    def send_message(self, message, raise_exceptions=True, **kwargs):
        kwargs = {
            AUTH_KEY_NAME: self.get_api_key(),
        }
        try:
            yield self.call(
                u"sdk.sendMessage",
                message,
                # Timeout is not currently working in the latest version of Autobahn...
                # options=CallOptions(timeout=1),
                **kwargs
            )
        except Exception as e:
            if raise_exceptions:
                raise
        finally:
            self.last_message_sent_at = time.time()

    def custom_init(self, custom_api_key_getter):
        ServerManagerBase.custom_init(self, custom_api_key_getter)

        self.application_runner = ApplicationRunner(
            url=get_wamp_url(),
            realm=WAMP_REALM,
            headers={AUTH_KEY_NAME: self.get_api_key()},
        )
        self.application_runner_deferred = self.application_runner.run(
            ServerManagerWAMP,
            start_reactor=False,
            auto_reconnect=True,
        )
        self.application_runner_deferred.addCallback(
            self.create_disconnect_monkeypatch(),
        )

    @inlineCallbacks
    def cleanup(self, sdk_run_uuid):
        # Try and flush any remaining messages
        clean = yield self.tick(sdk_run_uuid)
        returnValue(clean)

    def create_disconnect_monkeypatch(self):
        """
        Without this monkey patch, the onClose method would
        not be called in the scenario where the SDK tries to
        connect to the server, but is rejected due to an
        invalid API key:
        https://github.com/crossbario/autobahn-python/issues/559
        """
        def connect_success(proto):
            orig_on_close = proto.onClose

            def fake_on_close(*args, **kwargs):
                if proto._session is None:
                    self.onClose(*args, **kwargs)
                else:
                    orig_on_close(*args, **kwargs)

            proto.onClose = fake_on_close
        return connect_success

    def __init__(self, *args, **kwargs):
        ServerManagerBase.__init__(self, *args, **kwargs)
        WAMPSession.__init__(self, *args, **kwargs)