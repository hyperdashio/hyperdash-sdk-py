import os

import six


def get_base_url():
    return six.text_type(
        "{}/api/v1".format(os.environ.get(
            "HYPERDASH_SERVER",
            "https://hyperdash.io",
        ))
    )
