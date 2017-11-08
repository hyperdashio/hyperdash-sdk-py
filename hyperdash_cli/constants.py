import os

import six


GITHUB_OAUTH_START = "oauth/github/start"

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60

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
