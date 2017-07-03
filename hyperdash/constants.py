import os

import six


AUTH_KEY_NAME = "x-hyperdash-auth"
WAMP_ENDPOINT = "/api/v1/sdk/wamp"
WAMP_REALM = u"hyperdash.v1.sdk"


def get_base_url():
    return six.text_type(os.environ.get(
        "HYPERDASH_SERVER",
        "wss://hyperdash.io",
    ))


def get_wamp_url():
    return get_base_url() + WAMP_ENDPOINT
