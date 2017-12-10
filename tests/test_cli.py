# -*- coding: utf-8 -*-
import argparse
import json
import os

import requests
from threading import Thread

from six import StringIO
from six import PY2
from mock import patch, Mock
from nose.tools import assert_in

import hyperdash_cli
from mocks import init_mock_server
from hyperdash.constants import API_KEY_NAME
from hyperdash.constants import API_NAME_CLI_PIPE
from hyperdash.constants import API_NAME_CLI_RUN
from hyperdash.constants import API_NAME_CLI_TENSORBOARD
from hyperdash.constants import get_hyperdash_json_home_path
from hyperdash.constants import get_hyperdash_logs_home_path_for_job
from hyperdash.constants import get_hyperdash_version
from hyperdash.constants import VERSION_KEY_NAME


DEFAULT_API_KEY = "y9bhlYMBivCu8cBj6SQPAbwjxSqnbR1w23TtR9n9yOM="
DEFAULT_ACCESS_TOKEN = "72a84fc0-b272-480a-807d-fd4a40ee2a66"

server_sdk_headers = []
server_sdk_messages = []


class TestCLI(object):
    def setup(self):
        global server_sdk_messages
        global server_sdk_headers
        server_sdk_messages = []
        server_sdk_headers = []

    @classmethod
    def setup_class(_cls):
        request_handle_dict = init_mock_server()

        def setup(self):
            try:
                # Delete hyperdash.json file between tests
                os.remove(get_hyperdash_json_home_path())
            except FileNotFoundError:
                pass

        def user_signup(response):
            # Add response status code.
            response.send_response(requests.codes.ok)

            # Add response headers.
            response.send_header(
                'Content-Type', 'application/json; charset=utf-8')
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
            response.send_header(
                'Content-Type', 'application/json; charset=utf-8')
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
            response.send_header(
                'Content-Type', 'application/json; charset=utf-8')
            response.end_headers()

            # Add response content.
            response_content = json.dumps({
                "api_keys": [DEFAULT_API_KEY]
            })
            response.wfile.write(response_content.encode('utf-8'))

        def sdk_message(response):
            global server_sdk_messages
            global server_sdk_headers
            message = json.loads(response.rfile.read(
                int(response.headers["Content-Length"])).decode("utf-8"))

            # Store messages / headers so we can assert on them later
            server_sdk_messages.append(message)
            if PY2:
                server_sdk_headers.append(response.headers.dict)
            else:
                server_sdk_headers.append(response.headers)


            # Add response status code.
            response.send_response(requests.codes.ok)

            # Add response headers.
            response.send_header(
                'Content-Type', 'application/json; charset=utf-8')
            response.end_headers()

            # Add response content. In this case, we use the exact same response for
            # all messages from the SDK because the current implementation ignores the
            # body of the response unless there is an error.
            response_content = json.dumps({})

            response.wfile.write(response_content.encode('utf-8'))

        request_handle_dict[("POST", "/api/v1/users")] = user_signup
        request_handle_dict[("POST", "/api/v1/sessions")] = user_login
        request_handle_dict[("GET", "/api/v1/users/api_keys")] = user_api_keys
        request_handle_dict[("POST", "/api/v1/sdk/http")] = sdk_message

    def test_signup(self):
        vals = {
            ("Email address: ", ): "user@email.com",
            ("Company (optional): ", ): "Company",
            ("Password (8 characters or more): ", True): "Password",
        }

        def side_effect(*args):
            return vals[args]

        with patch('hyperdash_cli.cli.get_input', Mock(side_effect=side_effect)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.signup(argparse.Namespace(email=True))

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
            hyperdash_cli.login(argparse.Namespace(email=True))

        expected_output = [
            "Successfully logged in!",
            "We also installed: {} as your default API key".format(
                DEFAULT_API_KEY),
        ]
        for expected in expected_output:
            assert_in(expected, fake_out.getvalue())

    # This test is fairly primitive, but its enough to verify python2/3 compatibility
    def test_github(self):
        vals = {
            ("Access token: ", ): DEFAULT_ACCESS_TOKEN,
        }

        def side_effect(*args):
            return vals[args]

        with patch('hyperdash_cli.cli.get_input', Mock(side_effect=side_effect)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.github()

        expected_output = [
            "Successfully logged in!",
            "We also installed: {} as your default API key".format(
                DEFAULT_API_KEY),
        ]
        for expected in expected_output:
            assert_in(expected, fake_out.getvalue())

    def test_keys(self):
        with patch('hyperdash_cli.cli.get_access_token_from_file', Mock(return_value=DEFAULT_ACCESS_TOKEN)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.keys()

        expected_output = [
            "Below are the API Keys associated with you account:",
            "1) {}".format(DEFAULT_API_KEY),
        ]
        for expected in expected_output:
            assert_in(expected, fake_out.getvalue())

    def test_run(self):
        job_name = "some_job_name"
        with patch('hyperdash_cli.cli.get_access_token_from_file', Mock(return_value=DEFAULT_ACCESS_TOKEN)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.run(
                argparse.Namespace(
                    name=job_name,
                    args=[
                        "echo", "hello world", "&&",
                        "echo", "foo bar baz", "&&",
                        "python", "tests/test_script_for_run_test.py",
                    ]
                )
            )

        expected_output = [
            "hello world",
            "foo bar baz",
            "this is the test script",
            "字",
            "{'some_obj_key': 'some_value'}",
        ]
        for expected in expected_output:
            if PY2:
                assert_in(expected, fake_out.getvalue().encode("utf-8"))
                continue
            assert_in(expected, fake_out.getvalue())

        # Make sure correct API name / version headers are sent
        assert server_sdk_headers[0][API_KEY_NAME] == API_NAME_CLI_RUN
        assert server_sdk_headers[0][VERSION_KEY_NAME] == get_hyperdash_version()

        # Make sure logs were persisted
        log_dir = get_hyperdash_logs_home_path_for_job(job_name)
        latest_log_file = max([
            os.path.join(log_dir, filename) for
            filename in
            os.listdir(log_dir)
        ], key=os.path.getmtime)
        with open(latest_log_file, 'r') as log_file:
            data = log_file.read()
            for expected in expected_output:
                assert_in(expected, data)
        os.remove(latest_log_file)


    def test_tensorboard(self):
        job_name = "some_job_name"
        with patch('hyperdash_cli.cli.get_access_token_from_file', Mock(return_value=DEFAULT_ACCESS_TOKEN)), patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.tensorboard(
                argparse.Namespace(
                    name=job_name,
                    logdir="tests/test_tensorboard_logs",
                    backfill=True,
                ),
                is_test=True,
            )

        # This is not all the datapoints in the tensorboard logs, but only these ones are included
        # due to the default 1s sampling
        expected_metrics = [
            {u'timestamp': 1512945127487, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'job_name': u'some_job_name'}, u'type': u'run_started'},
            {u'timestamp': 1512945127489, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944548971, u'is_internal': False, u'name': u'loss', u'value': 2.3025853633880615}, u'type': u'metric'},
            {u'timestamp': 1512945127492, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944549971, u'is_internal': False, u'name': u'loss', u'value': 0.7624818682670593}, u'type': u'metric'},
            {u'timestamp': 1512945127495, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944550972, u'is_internal': False, u'name': u'loss', u'value': 0.5105720162391663}, u'type': u'metric'},
            {u'timestamp': 1512945127497, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944551976, u'is_internal': False, u'name': u'loss', u'value': 0.5286356210708618}, u'type': u'metric'},
            {u'timestamp': 1512945127500, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944553023, u'is_internal': False, u'name': u'loss', u'value': 0.455232173204422}, u'type': u'metric'},
            {u'timestamp': 1512945127503, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944554024, u'is_internal': False, u'name': u'loss', u'value': 0.372854620218277}, u'type': u'metric'},
            {u'timestamp': 1512945127505, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944555025, u'is_internal': False, u'name': u'loss', u'value': 0.4262654483318329}, u'type': u'metric'},
            {u'timestamp': 1512945127508, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944556025, u'is_internal': False, u'name': u'loss', u'value': 0.38998115062713623}, u'type': u'metric'},
            {u'timestamp': 1512945127510, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944557025, u'is_internal': False, u'name': u'loss', u'value': 0.38911107182502747}, u'type': u'metric'},
            {u'timestamp': 1512945127512, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944558026, u'is_internal': False, u'name': u'loss', u'value': 0.4348866641521454}, u'type': u'metric'},
            {u'timestamp': 1512945127516, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944559027, u'is_internal': False, u'name': u'loss', u'value': 0.286268413066864}, u'type': u'metric'},
            {u'timestamp': 1512945127519, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944560028, u'is_internal': False, u'name': u'loss', u'value': 0.3003489673137665}, u'type': u'metric'},
            {u'timestamp': 1512945127523, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944561029, u'is_internal': False, u'name': u'loss', u'value': 0.3317962884902954}, u'type': u'metric'},
            {u'timestamp': 1512945127525, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944562034, u'is_internal': False, u'name': u'loss', u'value': 0.27931177616119385}, u'type': u'metric'},
            {u'timestamp': 1512945127526, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944563042, u'is_internal': False, u'name': u'loss', u'value': 0.6486308574676514}, u'type': u'metric'},
            {u'timestamp': 1512945127528, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944564109, u'is_internal': False, u'name': u'loss', u'value': 0.5528809428215027}, u'type': u'metric'},
            {u'timestamp': 1512945127531, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944565113, u'is_internal': False, u'name': u'loss', u'value': 0.3118564486503601}, u'type': u'metric'},
            {u'timestamp': 1512945127542, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944566113, u'is_internal': False, u'name': u'loss', u'value': 0.48642101883888245}, u'type': u'metric'},
            {u'timestamp': 1512945127544, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944567114, u'is_internal': False, u'name': u'loss', u'value': 0.2462320178747177}, u'type': u'metric'},
            {u'timestamp': 1512945127549, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944568117, u'is_internal': False, u'name': u'loss', u'value': 0.2997052073478699}, u'type': u'metric'},
            {u'timestamp': 1512945127553, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944569119, u'is_internal': False, u'name': u'loss', u'value': 0.19338417053222656}, u'type': u'metric'},
            {u'timestamp': 1512945127557, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944570120, u'is_internal': False, u'name': u'loss', u'value': 0.4237367510795593}, u'type': u'metric'},
            {u'timestamp': 1512945127560, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944571121, u'is_internal': False, u'name': u'loss', u'value': 0.2270836979150772}, u'type': u'metric'},
            {u'timestamp': 1512945127561, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944548971, u'is_internal': False, u'name': u'accuracy', u'value': 0.14000000059604645}, u'type': u'metric'},
            {u'timestamp': 1512945127563, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944549971, u'is_internal': False, u'name': u'accuracy', u'value': 0.800000011920929}, u'type': u'metric'},
            {u'timestamp': 1512945127566, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944550972, u'is_internal': False, u'name': u'accuracy', u'value': 0.8999999761581421}, u'type': u'metric'},
            {u'timestamp': 1512945127568, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944551976, u'is_internal': False, u'name': u'accuracy', u'value': 0.8600000143051147}, u'type': u'metric'},
            {u'timestamp': 1512945127570, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944553023, u'is_internal': False, u'name': u'accuracy', u'value': 0.9100000262260437}, u'type': u'metric'},
            {u'timestamp': 1512945127573, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944554024, u'is_internal': False, u'name': u'accuracy', u'value': 0.8999999761581421}, u'type': u'metric'},
            {u'timestamp': 1512945127575, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944555025, u'is_internal': False, u'name': u'accuracy', u'value': 0.8899999856948853}, u'type': u'metric'},
            {u'timestamp': 1512945127578, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944556025, u'is_internal': False, u'name': u'accuracy', u'value': 0.8799999952316284}, u'type': u'metric'},
            {u'timestamp': 1512945127580, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944557025, u'is_internal': False, u'name': u'accuracy', u'value': 0.8899999856948853}, u'type': u'metric'},
            {u'timestamp': 1512945127582, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944558026, u'is_internal': False, u'name': u'accuracy', u'value': 0.8799999952316284}, u'type': u'metric'},
            {u'timestamp': 1512945127585, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944559027, u'is_internal': False, u'name': u'accuracy', u'value': 0.9599999785423279}, u'type': u'metric'},
            {u'timestamp': 1512945127587, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944560028, u'is_internal': False, u'name': u'accuracy', u'value': 0.8999999761581421}, u'type': u'metric'},
            {u'timestamp': 1512945127591, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944561029, u'is_internal': False, u'name': u'accuracy', u'value': 0.9200000166893005}, u'type': u'metric'},
            {u'timestamp': 1512945127593, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944562034, u'is_internal': False, u'name': u'accuracy', u'value': 0.9300000071525574}, u'type': u'metric'},
            {u'timestamp': 1512945127594, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944563042, u'is_internal': False, u'name': u'accuracy', u'value': 0.8500000238418579}, u'type': u'metric'},
            {u'timestamp': 1512945127596, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944564109, u'is_internal': False, u'name': u'accuracy', u'value': 0.8199999928474426}, u'type': u'metric'},
            {u'timestamp': 1512945127599, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944565113, u'is_internal': False, u'name': u'accuracy', u'value': 0.9300000071525574}, u'type': u'metric'},
            {u'timestamp': 1512945127602, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944566113, u'is_internal': False, u'name': u'accuracy', u'value': 0.8600000143051147}, u'type': u'metric'},
            {u'timestamp': 1512945127603, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944567114, u'is_internal': False, u'name': u'accuracy', u'value': 0.949999988079071}, u'type': u'metric'},
            {u'timestamp': 1512945127605, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944568117, u'is_internal': False, u'name': u'accuracy', u'value': 0.9300000071525574}, u'type': u'metric'},
            {u'timestamp': 1512945127608, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944569119, u'is_internal': False, u'name': u'accuracy', u'value': 0.9599999785423279}, u'type': u'metric'},
            {u'timestamp': 1512945127610, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944570120, u'is_internal': False, u'name': u'accuracy', u'value': 0.8799999952316284}, u'type': u'metric'},
            {u'timestamp': 1512945127612, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'timestamp': 1512944571121, u'is_internal': False, u'name': u'accuracy', u'value': 0.9300000071525574}, u'type': u'metric'},
            {u'timestamp': 1512945128493, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'body': u'This run of some_job_name ran for 0:00:01 and logs are available locally at: /Users/richie/.hyperdash/logs/some-job-name/some-job-name_2017-12-10t17-32-07-487283.log\n', u'uuid': u'2a00ed85-d9a0-4df5-ab2d-fee35fb1dd00', u'level': u'INFO'}, u'type': u'log'},
            {u'timestamp': 1512945128493, u'sdk_run_uuid': u'77972e75-6266-4d2a-94b7-25117b7dcd08', u'payload': {u'final_status': u'success'}, u'type': u'run_ended'}
        ]

        for i, message in enumerate(server_sdk_messages):
            if message['type'] == 'metric':
                assert message['payload'] == expected_metrics[i]['payload']
        
        # Make sure correct API name / version headers are sent
        assert server_sdk_headers[0][API_KEY_NAME] == API_NAME_CLI_TENSORBOARD
        assert server_sdk_headers[0][VERSION_KEY_NAME] == get_hyperdash_version()


    def test_pipe(self):
        job_name = "some_job_name"
        inputs = [
            "hello world",
            "foo bar baz",
            "this is the test script",
            "字",
            "{'some_obj_key': 'some_value'}",
        ]
        r_d, w_d = os.pipe()
        r_pipe = os.fdopen(r_d)
        w_pipe = os.fdopen(w_d, 'w')
        with patch('hyperdash_cli.cli.get_access_token_from_file', Mock(return_value=DEFAULT_ACCESS_TOKEN)), patch('sys.stdin', new=r_pipe), patch('sys.stdout', new=StringIO()) as fake_out:
            def writer():
                for input_str in inputs:
                    w_pipe.write(input_str)
                w_pipe.flush()
                w_pipe.close()
            writer_thread = Thread(target=writer)
            writer_thread.start()

            hyperdash_cli.pipe(
                argparse.Namespace(
                    name=job_name
                )
            )

        for expected in inputs:
            if PY2:
                assert_in(expected, fake_out.getvalue().encode("utf-8"))
                continue
            assert_in(expected, fake_out.getvalue())

        # Make sure correct API name / version headers are sent
        assert server_sdk_headers[0][API_KEY_NAME] == API_NAME_CLI_PIPE
        assert server_sdk_headers[0][VERSION_KEY_NAME] == get_hyperdash_version()

        # Make sure logs were persisted
        log_dir = get_hyperdash_logs_home_path_for_job(job_name)
        latest_log_file = max([
            os.path.join(log_dir, filename) for
            filename in
            os.listdir(log_dir)
        ], key=os.path.getmtime)
        with open(latest_log_file, 'r') as log_file:
            data = log_file.read()
            for expected in inputs:
                assert_in(expected, data)
        os.remove(latest_log_file)

    def test_version(self):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            hyperdash_cli.version()

        expected_output = [
            "hyperdash {}".format(get_hyperdash_version())
        ]
        for expected in expected_output:
            assert_in(expected, fake_out.getvalue())