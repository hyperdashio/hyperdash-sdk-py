import argparse
import errno
from getpass import getpass
import os
import subprocess
import time
from threading import Thread
import json
import sys

import requests

from six.moves import input
from six.moves.queue import Queue
from six import PY2

from hyperdash.constants import get_hyperdash_json_home_path
from hyperdash.constants import get_hyperdash_json_paths
from hyperdash import monitor

from .constants import get_base_url


def signup(args=None):
    email = get_input("Email address: ")
    password = get_input("Password (8 characters or more): ", True)

    print("Trying to sign you up now...")
    try:
        res = post_json("/users", {
            'email': email,
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

    _login(email, password)


def demo(args=None):
    from_file = get_api_key_from_file()
    from_env = get_api_key_from_env()
    api_key = from_env or from_file

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


def login(args=None):
    email = get_input("Email address: ")
    password = get_input("Password: ", True)
    success, default_api_key = _login(email, password)
    if success:
        print("Successfully logged in! We also installed: {} as your default API key".format(default_api_key))


def _login(email, password):
    try:
        response = post_json("/sessions", {
            'email': email,
            'password': password,
        })
    except Exception as e:
        print("Sorry we were unable to log you in, please try again.")
        return False, None

    response_body = response.json()
    if response.status_code != 200:
        message = response_body.get('message')
        if message:
            print(message)
            return False, None

    access_token = response_body['access_token']
    config = {'access_token': access_token}

    # Add API key if available
    api_keys = get_api_keys(access_token)
    if api_keys and len(api_keys) > 0:
        default_api_key = api_keys[0]    
        config['api_key'] = default_api_key
    else:
        print("Login failure: We were unable to retrieve your default API key.")
        return False, None

    write_hyperdash_json_file(config)
    return True, default_api_key


def get_api_keys(access_token):
    try:
        res = get_json("/users/api_keys", headers={
            'authorization': access_token,
        })
        res_json = res.json()
        if res.status_code != 200:
            message = res_json.get('message')
            if message:
                print(message)
            return None
        return res_json.get('api_keys')
    except Exception as e:
        print("Sorry we were unable to retrieve your API keys, please try again.")
        return None


def keys(args=None):
    from_file = get_access_token_from_file()
    from_env = get_access_token_from_env()
    access_token = from_file or from_env

    if not access_token:
        print("Not authorized.\n\n"
              "`hyperdash keys` is an authorized request available only to logged in users.\n"
              "Login with `hyperdash login` to authenticate as a user.\n\n")
        return

    api_keys = get_api_keys(access_token)
    if api_keys is None:
        return

    print("\nBelow are the API Keys associated with you account:\n\n")

    for i, api_key in enumerate(api_keys):
        print("    {}) {}".format(i+1, api_key))

    print("\n")


def run(args):
    @monitor(args.name)
    def wrapped():
        # Python detects when its connected to a pipe and buffers output.
        # Spawn the users program with the PYTHONUNBUFFERED environment 
        # variable set in case they are running a Python program.
        subprocess_env = os.environ.copy()
        subprocess_env["PYTHONUNBUFFERED"]="1"
        # Spawn a subprocess with the user's command
        p = subprocess.Popen(
            ' '.join(args.args),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            env=subprocess_env,
        )

        # The subprocess's output will be written to the associated
        # pipes. In order for the @monitor decorator to have access
        # to them, we need to read them out and write them to
        # stdout/stderr respectively (which have been redirected by
        # the monitor decorator)
        def stdout_loop():
            while True:
                data = p.stdout.readline()
                if not data:
                    return
                # In PY2 data is str, in PY3 its bytes
                if PY2:
                    sys.stdout.write(data)
                    continue
                sys.stdout.write(data.decode("utf-8", "ignore"))
        def stderr_loop():
            while True:
                data = p.stderr.readline()
                if not data:
                    return
                # In PY2 data is str, in PY3 its bytes
                if PY2:
                    sys.stdout.write(data)
                    continue
                sys.stdout.write(data.decode("utf-8", "ignore"))

        stdout_thread = Thread(target=stdout_loop)
        stderr_thread = Thread(target=stderr_loop)
        stdout_thread.start()
        stderr_thread.start()
        # Wait for the subprocess to finish executing
        p.wait()
        # Threads will exit as soon as their associated pipes are closed by the operating system
        stdout_thread.join()
        stderr_thread.join()
    wrapped()


def get_input(prompt, sensitive=False):
    if sensitive:
        return getpass(prompt)
    return input(prompt)


def get_json(path, **kwargs):
    return requests.get("{}{}".format(get_base_url(), path), **kwargs)

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


def get_access_token_from_file():
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

    return parsed.get('access_token') if parsed else None


def get_access_token_from_env():
    return os.environ.get("HYPERDASH_ACCESS_TOKEN")


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

    login_parser = subparsers.add_parser('login')
    login_parser.set_defaults(func=login)

    keys_parser = subparsers.add_parser('keys')
    keys_parser.set_defaults(func=keys)

    run_parser = subparsers.add_parser('run')
    run_parser.add_argument('--name', '-name', '--n', '-n', required=True)
    run_parser.add_argument('args', nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=run)

    args = parser.parse_args()
    args.func(args)
