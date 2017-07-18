import argparse
import errno
from getpass import getpass
import os
import time
import json

import requests

from six.moves import input

from hyperdash.constants import get_hyperdash_json_home_path
from hyperdash.constants import get_hyperdash_json_paths
from hyperdash import monitor

from .constants import get_base_url


def signup():
    email = get_input("Email address: ")
    company = get_input("Company (optional): ")
    password = get_input("Password (8 characters or more): ", True)

    print("Trying to sign you up now...")
    try:
        res = post_json("/users", {
            'email': email,
            'company': company,
            'password': password,
        })
    except Exception as e:
        print("Sorry we were unable to sign you up, please try again.")
        return

    res_body = res.json()
    if res.status_code != 200:
        message = res_body.get('message')
        if message:
            print(message)
            return

    print("Congratulations on signing up!")
    api_key = res_body['api_key']
    print("Your API key is: {}".format(api_key))

    write_hyperdash_json_file({
        'api_key': api_key
    })
    print("""
        We stored your API key in {}
        and we'll use that as the default for future jobs.

        If you want to see Hyperdash in action, run `hyperdash demo`
        and then install our mobile app to monitor your job in realtime.
    """.format(get_hyperdash_json_home_path())
    )

    login(email, password)


def demo():
    from_file = get_api_key_from_file()
    from_env = get_api_key_from_env()
    api_key = from_file or from_env

    if not api_key:
        print("""
            `hyperdash demo` requires a Hyperdash API key. Try setting your API key in the
            HYPERDASH_API_KEY environment variable, or in a hyperdash.json file in the local
            directory or your user's home directory with the following format:

            {
                "api_key": "<YOUR_API_KEY>"
            }
        """)
        return

    print("""
        Running the following program:

        from hyperdash import monitor


        @monitor("dogs vs. cats")
        def train_dogs_vs_cats():
            print("Begin training model to distinguish dogs from cats...")
            print("Epoch 1, accuracy: 50%")
            time.sleep(5)
            print("Epoch 2, accuracy: 75%")
            time.sleep(5)
            print("Epoch 3, accuracy: 85%")
            time.sleep(5)
            print("Epoch 4, accuracy: 95%")
            time.sleep(5)
            print("Epoch 5, accuracy: 100%")
    """)

    @monitor("dogs vs. cats")
    def train_dogs_vs_cats():
        print("Begin training model to distinguish dogs from cats...")
        print("Epoch 1, accuracy: 50%")
        time.sleep(5)
        print("Epoch 2, accuracy: 75%")
        time.sleep(5)
        print("Epoch 3, accuracy: 85%")
        time.sleep(5)
        print("Epoch 4, accuracy: 95%")
        time.sleep(5)
        print("Epoch 5, accuracy: 100%")

    train_dogs_vs_cats()


def login(email=None, password=None):
    if not email:
        email = get_input("Email Address:")
    if not password:
        password = get_input("Password:", True)

    try:
        response = post_json("/sessions", {
            'email': email,
            'password': password,
        })
    except Exception as e:
        print("Sorry we were unable to log you in, please try again.")
        return

    response_body = response.json()
    if response.status_code == 422 or response.status_code == 401:
        message = response_body.get('message')
        if message:
            print(message)
            return

    write_hyperdash_json_file({
        'access_token': response_body['access_token'],
    })
    print("Successfully logged in!")

def get_input(prompt, sensitive=False):
    if sensitive:
        return getpass(prompt)
    return input(prompt)


def post_json(path, data):
    return requests.post(
        "{}{}".format(get_base_url(), path),
        json=data,
    )


def write_hyperdash_json_file(hyperdash_json):
    path = get_hyperdash_json_home_path()

    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    try:
        # Open for read/write, but will not create file
        with open(path, 'r+') as f:
            write_hyperdash_json_helper(f, hyperdash_json)
    except IOError:
        # Open for read/write but will truncate if it already exists
        with open(path, 'w+') as f:
            write_hyperdash_json_helper(f, hyperdash_json)


def write_hyperdash_json_helper(file, hyperdash_json):
    data = file.read()

    existing = {}
    if len(data) > 0:
        try:
            existing = json.loads(data)
        except ValueError:
            raise Exception("{} is not valid JSON!".format(get_hyperdash_json_home_path()))

    existing.update(hyperdash_json)

    # Seek back to beginning before we write
    file.seek(0)
    file.write(json.dumps(existing))
    file.write("\n")
    file.truncate()


def get_api_key_from_file():
    parsed = None
    for path in get_hyperdash_json_paths():
        try:
            with open(path, "r") as f:
                try:
                    parsed = json.load(f)
                except ValueError:
                    print("hyperdash.json is not valid JSON")
                    return None
        except IOError:
            continue

    return parsed.get('api_key') if parsed else None


def get_api_key_from_env():
    return os.environ.get("HYPERDASH_API_KEY")


def main():
    parser = argparse.ArgumentParser(description='The HyperDash SDK')
    subparsers = parser.add_subparsers(
        title='subcommands',
        description='valid subcommands',
        help='additional help',
    )

    signup_parser = subparsers.add_parser('signup')
    signup_parser.set_defaults(func=signup)

    demo_parser = subparsers.add_parser('demo')
    demo_parser.set_defaults(func=demo)

    demo_parser = subparsers.add_parser('login')
    demo_parser.set_defaults(func=login)

    args = parser.parse_args()
    args.func()
