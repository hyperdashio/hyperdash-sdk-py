import os
import sys

import six


AUTH_KEY_NAME = "x-hyperdash-auth"
HTTP_ENDPOINT = "/api/v1/sdk/http"
WAMP_ENDPOINT = "/api/v1/sdk/wamp"
WAMP_REALM = u"hyperdash.v1.sdk"
CACHE_API_KEY_FOR_SECONDS = 300


def get_base_http_url():
    return six.text_type(os.environ.get(
        "HYPERDASH_SERVER",
        "https://hyperdash.io",
    ))


def get_http_url():
    return get_base_http_url() + HTTP_ENDPOINT


def get_base_wamp_url():
    return six.text_type(os.environ.get(
        "HYPERDASH_SERVER",
        "wss://hyperdash.io",
    ))


def get_wamp_url():
    return get_base_wamp_url() + WAMP_ENDPOINT


def get_hyperdash_json_paths():
    return [
        path for
        path in
        [get_hyperdash_json_home_path(), get_hyperdash_json_local_path()]
        if path
    ]


def get_hyperdash_json_home_path():
    return os.path.join(os.path.expanduser("~/.hyperdash"), "hyperdash.json")


def get_hyperdash_json_local_path():
    main = sys.modules["__main__"]
    if not hasattr(main, "__file__"):
        return None

    main_file_path = os.path.abspath(main.__file__)
    root_folder = os.path.dirname(main_file_path)
    return os.path.join(root_folder, "hyperdash.json")
