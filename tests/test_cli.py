from six import StringIO
from mock import patch, Mock
from nose.tools import assert_dict_contains_subset, assert_list_equal, assert_true
import requests
import json

import hyperdash_cli
from mocks import init_mock_server


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
                "api_key":"FI2fKYloUzqy2C/IK/pLR8xHeJpn7ucwLFgCBAZNhf0=",
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
                "user_uuid": "72a84fc0-b272-480a-807d-fd4a40ee2a66",
                "api_key":"FI2fKYloUzqy2C/IK/pLR8xHeJpn7ucwLFgCBAZNhf0=",
            })
            response.wfile.write(response_content.encode('utf-8'))

        request_handle_dict[("POST", "/api/v1/users")] = user_signup
        request_handle_dict[("POST", "/api/v1/sessions")] = user_login

    def test_signup(self):
        vals = {
            ("Email address: ", ): "user@email.com",
            ("Company (optional): ", ): "Company",
            ("Password (8 characters or more): ", True): "Password",
        }
        def side_effect(*args):
            return vals[args]

        with patch('hyperdash_cli.cli.get_input', Mock(side_effect=side_effect)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.cli.signup()

        a = fake_out.getvalue()
        assert a == "", a
