import argparse
from contextlib import closing
import errno
from getpass import getpass
import os
import subprocess
import time
from threading import Thread
import json
import socket
import sys
import webbrowser

import requests

from six.moves import input
from six.moves import xrange
from six.moves.queue import Queue
from six.moves.urllib.parse import urlparse, parse_qs, urlencode
from six.moves import BaseHTTPServer

from six import PY2

from hyperdash.constants import API_NAME_CLI_PIPE
from hyperdash.constants import API_NAME_CLI_RUN
from hyperdash.constants import get_hyperdash_json_home_path
from hyperdash.constants import get_hyperdash_json_paths
from hyperdash.constants import get_hyperdash_version
from hyperdash import monitor
from hyperdash.monitor import _monitor

from .constants import get_base_url
from .constants import get_base_http_url
from .constants import GITHUB_OAUTH_START
from .constants import ONE_YEAR_IN_SECONDS
from .constants import LOOPBACK


def signup(args=None):
    if not (args.email or args.github):
        print("To signup with your email address, run `hd signup --email`. Alternatively, you can signup via Github by running `hd signup --github")
        return

    if args.email:
        _signup_email(args)
        return
    
    if args.github:
        github(args)
        return


def _signup_email(args):
    email = get_input("Email address: ")
    password = get_input("Password (8 characters or more): ", True)

    print("Trying to sign you up now...")
    try:
        res = post_json("/users", {
            "email": email,
            "password": password,
            "client": "cli",
        })
    except Exception as e:
        print("Sorry we were unable to sign you up, please try again.")
        return

    res_body = res.json()
    if res.status_code != 200:
        message = res_body.get("message")
        if message:
            print(message)
            return

    print("Congratulations on signing up!")
    api_key = res_body["api_key"]
    print("Your API key is: {}".format(api_key))

    write_hyperdash_json_file({
        "api_key": api_key
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

    from hyperdash import Experiment
    exp = Experiment("Dogs vs. Cats")

    # Parameters
    estimators = exp.param("Estimators", 500)
    epochs = exp.param("Epochs", 5)
    batch = exp.param("Batch Size", 64)

    for epoch in xrange(1, epochs + 1):
        accuracy = 1. - 1./epoch
        loss = float(epochs - epoch)/epochs
        print("Training model (epoch {})".format(epoch))
        time.sleep(1)

        # Metrics
        exp.metric("Accuracy", accuracy)
        exp.metric("Loss", loss)

    exp.end()
    """)
    from hyperdash import Experiment
    exp = Experiment("Dogs vs. Cats")

    # Parameters
    estimators = exp.param("Estimators", 500)
    epochs = exp.param("Epochs", 5)
    batch = exp.param("Batch Size", 64)

    for epoch in xrange(epochs):
        print("Training model (epoch {})".format(epoch))

        accuracy = 1. - 1./(epoch + 1)
        loss = float(epochs - epoch)/(epochs + 1)

        # Metrics
        exp.metric("Accuracy", accuracy)
        exp.metric("Loss", loss)

        time.sleep(1)

    exp.end()


def github(args=None):
    port = _find_available_port()
    if not port:
        print("Github sign in requires an open port, please open port 3000.")

    # Signal when the HTTP server has started
    server_started_queue = Queue()
    # Signal when we have the access token
    access_token_queue = Queue()

    # Server that we will run in the background to accept a post-OAuth redirect from
    # the Hyperdash server which will contain the user's access token
    def start_server():
        class OAuthRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_path = urlparse(self.path)
                query = parse_qs(parsed_path.query)
                access_token = query["access_token"][0] if "access_token" in query else None
                if not access_token:
                    print("Something went wrong! Please try again.")
                    sys.exit()
                print("Access token auto-detected!")
                access_token_queue.put(access_token)
                # Redirect user's browser
                self.send_response(301)
                self.send_header("Location","{}/{}".format(get_base_http_url(), "/oauth/github/success"))
                self.end_headers()
            # Silence logs
            def log_message(self, _format, *args):
                return

        server = BaseHTTPServer.HTTPServer((LOOPBACK, port), OAuthRedirectHandler)
        server_started_queue.put(True)
        server.handle_request()
    
    server_thread = Thread(target=start_server)
    # Prevent server_thread from preventing program shutdown
    server_thread.setDaemon(True)
    server_thread.start()

    url = "{}/{}".format(get_base_http_url(), GITHUB_OAUTH_START)
    auto_login_query_args = {
        "state": "client_cli_auto:{}".format(port),
    }
    auto_login_url = "{}?{}".format(url, urlencode(auto_login_query_args))
    
    # Copy
    manual_login_query_args = dict(auto_login_query_args)
    manual_login_query_args["state"] = "client_cli_manual"
    manual_login_url = "{}?{}".format(url, urlencode(manual_login_query_args))

    print("Opening browser, please wait. If something goes wrong, press CTRL+C to cancel.")
    print("\033[1m SSH'd into a remote machine, or just don't have access to a browser? Open this link in any browser and then copy/paste the provided access token: \033[4m{}\033[0m \033[0m".format(manual_login_url))

    # If the user doesn't have programatic access to a browser, then we need to give them
    # the option of opening a URL manually and copy-pasting the access token into the CLI.
    # We spin this up in a separate thread so that it doesn't block the happy path where
    # the browser is available and we're able to auto-detect the access token
    manual_entry_thread_started_queue = Queue()
    def manual_entry():
        print("Waiting for Github OAuth to complete.")
        print("If something goes wrong, press CTRL+C to cancel.")        
        manual_entry_thread_started_queue.put(True)
        access_token = get_input("Access token: ")
        access_token_queue.put(access_token)
            
    manual_entry_thread = Thread(target=manual_entry)
    # Prevent manual_entry_thread from preventing program shutdown
    manual_entry_thread.setDaemon(True)
    manual_entry_thread.start()

    # Wait until the server and manual entry threads have started before opening the
    # user's browser to prevent a race condition where the Hyperdash server
    # redirects with an access token but the Python server isn't ready yet.
    # 
    # Also, we set the timeout to ONE_YEAR_IN_SECONDS because without a timeout,
    # the .get() call on the queue can not be interrupted with CTRL+C.
    server_started_queue.get(block=True, timeout=ONE_YEAR_IN_SECONDS)
    manual_entry_thread_started_queue.get(block=True, timeout=ONE_YEAR_IN_SECONDS)
    # Blocks until browser opens, but doesn't wait for user to close it
    webbrowser.open_new_tab(auto_login_url)


    # Wait for the Hyperdash server to redirect with the access token to our embedded
    # server, or for the user to manually enter an access token. Whichever happens
    # first.
    access_token = access_token_queue.get(block=True, timeout=ONE_YEAR_IN_SECONDS)
    # Use the access token to retrieve the user's API key and store a valid
    # hyperdash.json file
    success, default_api_key = _after_access_token_login(access_token)
    if success:
        print("Successfully logged in! We also installed: {} as your default API key".format(
            default_api_key))


def _find_available_port():
    for cur_port in xrange(3000, 9000):
        is_open = _is_port_open(LOOPBACK, cur_port)
        if is_open:
            return cur_port
    return None


def _is_port_open(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.bind((host, port))
        sock.listen(5)
        sock.close()
    except (socket.error, socket.timeout):
        return False
    return True


def login(args=None):
    if not (args.email or args.github):
        print("To login with your email address, run `hd login --email`. Alternatively, you can login via Github by running `hd login --github")
        return

    if args.email:
        email = get_input("Email address: ")
        password = get_input("Password: ", True)
        success, default_api_key = _login(email, password)
        if success:
            print("Successfully logged in! We also installed: {} as your default API key".format(
                default_api_key))
        return
    
    if args.github:
        github(args)
        return


def _login(email, password):
    try:
        response = post_json("/sessions", {
            "email": email,
            "password": password,
        })
    except Exception as e:
        print("Sorry we were unable to log you in, please try again.")
        return False, None

    response_body = response.json()
    if response.status_code != 200:
        message = response_body.get("message")
        if message:
            print(message)
            return False, None

    access_token = response_body["access_token"]
    return _after_access_token_login(access_token)


def _after_access_token_login(access_token):
    config = {"access_token": access_token}

    # Add API key if available
    api_keys = get_api_keys(access_token)
    if api_keys and len(api_keys) > 0:
        default_api_key = api_keys[0]
        config["api_key"] = default_api_key
    else:
        print("Login failure: We were unable to retrieve your default API key.")
        return False, None

    write_hyperdash_json_file(config)
    return True, default_api_key


def get_api_keys(access_token):
    try:
        res = get_json("/users/api_keys", headers={
            "authorization": access_token,
        })
        res_json = res.json()
        if res.status_code != 200:
            message = res_json.get("message")
            if message:
                print(message)
            return None
        return res_json.get("api_keys")
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
        print("    {}) {}".format(i + 1, api_key))

    print("\n")


def run(args):
    @_monitor(args.name, api_key_getter=None, capture_io=True, api_name=API_NAME_CLI_RUN)
    def wrapped():
        # Python detects when its connected to a pipe and buffers output.
        # Spawn the users program with the PYTHONUNBUFFERED environment
        # variable set in case they are running a Python program.
        subprocess_env = os.environ.copy()
        subprocess_env["PYTHONUNBUFFERED"] = "1"
        # Spawn a subprocess with the user's command
        p = subprocess.Popen(
            " ".join(args.args),
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
            _connect_streams(p.stdout, sys.stdout)

        def stderr_loop():
            _connect_streams(p.stderr, sys.stderr)

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


def pipe(args):
    @_monitor(args.name, api_key_getter=None, capture_io=True, api_name=API_NAME_CLI_PIPE)
    def wrapped():
        # Read STDIN and write it to STDOUT so it shows up in the terminal and is
        # captured by the monitor decorator
        if PY2:
            in_stream = sys.stdin
        else:
            in_stream = sys.stdin.buffer
        _connect_streams(in_stream, sys.stdout)
    wrapped()


# Reads a pipe one character at a time, yielding
# buffers everytime it encounters whitespace. This
# allows us read the pipe as fast as possible.
#
# We yield everytime we encounter whitespace instead
# of on every byte because yielding every byte individually
# would break the UTF-8 decoding of multi-byte characters.
#
# Before this we were using readline() which works in most
# cases, but breaks for scripts that use loading bars
# like tqdm which do not output a \n everytime they
# update. Using read() doesn't work either because there
# is no guarantee of when that will be flushed so
# terminal updates can be delayed.
def _gen_tokens_from_stream(stream):
    buf = []
    while True:
        # read one byte        
        b = stream.read(1)
        # We're done
        if not b:
            if buf:
                # Yield what we have
                yield b"".join(buf)
            return
        # If its whitespace, yield what we have including the whitespace
        if b.isspace() and buf:
            yield b"".join(buf) + b
            buf = []
        # Otherwise grow the buf
        else:
            buf.append(b)


def _connect_streams(in_stream, out_stream):
    """Connects two streams and blocks until the input stream is closed."""
    for data in _gen_tokens_from_stream(in_stream):
        # In PY2 data is str, in PY3 its bytes
        if PY2:
            out_stream.write(data)
        else:
            out_stream.write(data.decode("utf-8", "ignore"))


def version(args=None):
    print("hyperdash {}".format(get_hyperdash_version()))


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
        with open(path, "r+") as f:
            write_hyperdash_json_helper(f, hyperdash_json)
    except IOError:
        # Open for read/write but will truncate if it already exists
        with open(path, "w+") as f:
            write_hyperdash_json_helper(f, hyperdash_json)


def write_hyperdash_json_helper(file, hyperdash_json):
    data = file.read()

    existing = {}
    if len(data) > 0:
        try:
            existing = json.loads(data)
        except ValueError:
            raise Exception("{} is not valid JSON!".format(
                get_hyperdash_json_home_path()))

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

    return parsed.get("access_token") if parsed else None


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

    return parsed.get("api_key") if parsed else None


def get_api_key_from_env():
    return os.environ.get("HYPERDASH_API_KEY")


def main():
    parser = argparse.ArgumentParser(description="The HyperDash SDK")
    subparsers = parser.add_subparsers(
        title="subcommands",
        description="valid subcommands",
        help="additional help",
        dest="subcommand"
    )
    subparsers.required = True

    signup_parser = subparsers.add_parser("signup")
    signup_parser.add_argument("--email", "-email", required=False, action='store_true')
    signup_parser.add_argument("--github", "-github", required=False, action='store_true')
    signup_parser.set_defaults(func=signup)

    demo_parser = subparsers.add_parser("demo")
    demo_parser.set_defaults(func=demo)

    login_parser = subparsers.add_parser("login")
    login_parser.add_argument("--email", "-email", required=False, action='store_true')
    login_parser.add_argument("--github", "-github", required=False, action='store_true')
    login_parser.set_defaults(func=login)

    github_parser = subparsers.add_parser("github")
    github_parser.set_defaults(func=github)

    keys_parser = subparsers.add_parser("keys")
    keys_parser.set_defaults(func=keys)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--name", "-name", "--n", "-n", required=True)
    run_parser.add_argument("args", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=run)

    pipe_parser = subparsers.add_parser("pipe")
    pipe_parser.add_argument("--name", "-name", "--n", "-n", required=True)
    pipe_parser.set_defaults(func=pipe)

    keys_parser = subparsers.add_parser("version")
    keys_parser.set_defaults(func=version)

    args = parser.parse_args()
    args.func(args)
