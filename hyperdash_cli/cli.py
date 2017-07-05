import argparse
from getpass import getpass
import os
import time
import json

from six.moves.urllib.parse import urlencode
from six.moves.urllib.request import urlopen
from six.moves import input

from .constants import get_base_url
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
    print("Your API key is: {}".format(response_body['api_key']))


def test():
    if not os.environ.get('HYPERDASH_API_KEY'):
        raise Exception("`hyperdash test` requires the HYPERDASH_API_KEY environment variable to be present")

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
        "{}/api/v1/users".format(get_base_url()),
        bytes(json.dumps(data).encode('utf8')),
    )


def main():
    parser = argparse.ArgumentParser(description='The HyperDash SDK')
    subparsers = parser.add_subparsers(
        title='subcommands',
        description='valid subcommands',
        help='additional help',
    )

    signup_parser = subparsers.add_parser('signup')
    signup_parser.set_defaults(func=signup)

    test_parser = subparsers.add_parser('test')
    test_parser.set_defaults(func=test)

    args = parser.parse_args()
    args.func()
