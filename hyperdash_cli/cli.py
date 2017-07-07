import argparse
from getpass import getpass
import os
import time
import json

from six.moves.urllib.parse import urlencode
from six.moves.urllib.request import urlopen
from six.moves import input

from .constants import get_base_url
from hyperdash.constants import get_hyperdash_json_paths, get_hyperdash_json_home_path
from hyperdash.sdk import monitor


def signup():
    email = get_input("Email address (must be valid):")
    company = get_input("Company:")
    password = get_input("Password (must be at least 8 characters):", True)

    print("Trying to sign you up now...")
    try:
        response = post_json({
            'email': email,
            'company': company,
            'password': password,
        })
    except Exception as e:
        if hasattr(e, 'code') and e.code == 422:
            body = json.loads(e.read())
            message = body.get('message')
            if message:
                print(message)
                return
            print(body['message'])
        print("Sorry something went wrong, please try again.")
        return

    response_body = json.loads(response.read())
    print("Congratulations on signing up!")
    api_key = response_body['api_key']
    print("Your API key is: {}".format(api_key))

    write_hyperdash_json_file({
        'api_key': api_key
    })

    print("""
        We stored your API key in {} 
        and we'll use that as the default for future jobs!

        If you want to see Hyperdash in action, install our
        mobile app and then run `hyperdash demo`
    """.format(get_hyperdash_json_home_path())
    )


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

        @monitor("dogs vs. cats")
        def train_dogs_vs_cats():
            print("Begin training model to distinguish dogs from cats...")
            print("Epoch 1, accuracy: 50%")
            time.sleep(2)
            print("Epoch 2, accuracy: 75%")
            time.sleep(2)
            print("Epoch 3, accuracy: 100%")
    """)

    @monitor("dogs vs. cats")
    def train_dogs_vs_cats():
        print("Begin training model to distinguish dogs from cats...")
        print("Epoch 1, accuracy: 50%")
        time.sleep(2)
        print("Epoch 2, accuracy: 75%")
        time.sleep(2)
        print("Epoch 3, accuracy: 100%")

    train_dogs_vs_cats()


def get_input(prompt, sensitive=False):
    if sensitive:
        return getpass(prompt)
    return input(prompt)


def post_json(data):
    return urlopen(
        "{}/users".format(get_base_url()),
        bytes(json.dumps(data).encode('utf8')),
    )


def write_hyperdash_json_file(hyperdash_json):
    with open(get_hyperdash_json_home_path(), 'w') as f:
        json.dump(hyperdash_json, f)


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

    args = parser.parse_args()
    args.func()
