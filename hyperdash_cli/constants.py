import os

import six


GITHUB_OAUTH_START = "oauth/github/start"

THREADING_TIMEOUT_MAX = 4294967  # Maximum allowed threading.TIMEOUT_MAX in Python 3.6

LOOPBACK = "127.0.0.1"


def get_base_http_url():
    return six.text_type(os.environ.get(
        "HYPERDASH_SERVER",
        "https://hyperdash.io",
    ))


def get_base_url():
    return six.text_type(
        "{}/api/v1".format(os.environ.get(
            "HYPERDASH_SERVER",
            "https://hyperdash.io",
        ))
    )
