import os

import six


GITHUB_CLIENT_ID = "4793c654216adde7a478"
GITHUB_OAUTH_SCOPES = ["user:email"]
GITHUB_REDIRECT_URI_PATH = "oauth/github/callback"

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60


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
