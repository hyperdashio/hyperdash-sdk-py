import os


AUTH_HEADER_KEY = "x-hyperdash-auth"
WAMP_ENDPOINT = "/api/v1/sdk/wamp"
WAMP_REALM = u"hyperdash.v1.sdk"


def get_base_url():
    environment = os.environ.get("HYPERDASH_ENVIRONMENT")
    if environment == "dev":
        return u"ws://127.0.0.1:4000"
    return u"wss://hyperdash.io"


def get_wamp_url():
    return get_base_url() + WAMP_ENDPOINT
