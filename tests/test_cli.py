from six import StringIO
from mock import patch, Mock
from nose.tools import assert_in
import requests
import json

import hyperdash_cli
from mocks import init_mock_server

DEFAULT_API_KEY = "y9bhlYMBivCu8cBj6SQPAbwjxSqnbR1w23TtR9n9yOM="

class TestCLI(object):
    @classmethod
    def setup_class(_cls):
        request_handle_dict = init_mock_server()

        def user_signup(response):
            # Add response status code.
            response.send_response(requests.codes.ok)

            # Add response headers.
            response.send_header('Content-Type', 'application/json; charset=utf-8')
            response.end_headers()

            # Add response content.
            response_content = json.dumps({
                "user_uuid": "72a84fc0-b272-480a-807d-fd4a40ee2a66",
                "api_key": DEFAULT_API_KEY,
            })
            response.wfile.write(response_content.encode('utf-8'))

        def user_login(response):
            # Add response status code.
            response.send_response(requests.codes.ok)

            # Add response headers.
            response.send_header('Content-Type', 'application/json; charset=utf-8')
            response.end_headers()

            # Add response content.
            response_content = json.dumps({
                "access_token": "72a84fc0-b272-480a-807d-fd4a40ee2a66"
            })
            response.wfile.write(response_content.encode('utf-8'))

        def user_api_keys(response):
            # Add response status code.
            response.send_response(requests.codes.ok)

            # Add response headers.
            response.send_header('Content-Type', 'application/json; charset=utf-8')
            response.end_headers()

            # Add response content.
            response_content = json.dumps({
                "api_keys": [DEFAULT_API_KEY]
            })
            response.wfile.write(response_content.encode('utf-8'))

        request_handle_dict[("POST", "/api/v1/users")] = user_signup
        request_handle_dict[("POST", "/api/v1/sessions")] = user_login
        request_handle_dict[("GET", "/api/v1/users/api_keys")] = user_api_keys

    def test_signup(self):
        vals = {
            ("Email address: ", ): "user@email.com",
            ("Company (optional): ", ): "Company",
            ("Password (8 characters or more): ", True): "Password",
        }
        def side_effect(*args):
            return vals[args]

        with patch('hyperdash_cli.cli.get_input', Mock(side_effect=side_effect)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.signup()

        expected_output = [
            "Trying to sign you up now...",
            "Congratulations on signing up!",
            "Your API key is: {}".format(DEFAULT_API_KEY),
            "We stored your API key in",
            "If you want to see Hyperdash in action, run `hyperdash demo`",
            "and then install our mobile app to monitor your job in realtime.",
        ]
        for expected in expected_output:
            assert_in(expected, fake_out.getvalue())

    def test_login(self):
        vals = {
            ("Email address: ", ): "user@email.com",
            ("Password: ", True): "Password",
        }
        def side_effect(*args):
            return vals[args]

        with patch('hyperdash_cli.cli.get_input', Mock(side_effect=side_effect)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.login()

        expected_output = [
            "Successfully logged in!",
            "We also installed: {} as your default API key".format(DEFAULT_API_KEY),
        ]
        for expected in expected_output:
            assert_in(expected, fake_out.getvalue())

    def test_keys(self):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.keys()

        expected_output = [
            "Below are the API Keys associated with you account:",
            "1) {}".format(DEFAULT_API_KEY),
        ]
        for expected in expected_output:
            assert_in(expected, fake_out.getvalue())
