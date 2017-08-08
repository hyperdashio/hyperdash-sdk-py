import os
import sys

import six

from slugify import slugify

AUTH_KEY_NAME = "x-hyperdash-auth"
HTTP_ENDPOINT = "/api/v1/sdk/http"
CACHE_API_KEY_FOR_SECONDS = 300


def get_base_http_url():
    return six.text_type(os.environ.get(
        "HYPERDASH_SERVER",
        "https://hyperdash.io",
    ))


def get_http_url():
    return get_base_http_url() + HTTP_ENDPOINT


def get_hyperdash_json_paths():
    return [
        path for
        path in
        [get_hyperdash_json_home_path(), get_hyperdash_json_local_path()]
        if path
    ]


def get_hyperdash_home_path():
    return os.path.join(os.path.expanduser("~"), ".hyperdash")


def get_hyperdash_json_home_path():
    return os.path.join(get_hyperdash_home_path(), "hyperdash.json")


def get_hyperdash_logs_home_path():
    return os.path.join(get_hyperdash_home_path(), "logs")


def get_hyperdash_logs_home_path_for_job(job):
    return os.path.join(get_hyperdash_logs_home_path(), slugify(job))


def get_hyperdash_local_path():
    main = sys.modules["__main__"]
    if not hasattr(main, "__file__"):
        return None

    main_file_path = os.path.abspath(main.__file__)
    return os.path.dirname(main_file_path)


def get_hyperdash_json_local_path():
    local_path = get_hyperdash_local_path()
    if not local_path:
        return None
    return os.path.join(local_path, "hyperdash.json")
