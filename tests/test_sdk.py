from six import StringIO
from mock import patch, Mock
from nose.tools import assert_dict_contains_subset, assert_list_equal, assert_true
import requests
import json
import time

from hyperdash import monitor
from mocks import init_mock_server


class TestSDK(object):
    @classmethod
    def setup_class(_cls):
        request_handle_dict = init_mock_server()

        def sdk_message(response):
            # Add response status code.
            response.send_response(requests.codes.ok)

            # Add response headers.
            response.send_header('Content-Type', 'application/json; charset=utf-8')
            response.end_headers()

            # Add response content.
            response_content = json.dumps({})

            response.wfile.write(response_content.encode('utf-8'))

        request_handle_dict[("POST", "/api/v1/sdk/http")] = sdk_message

    # The server will return the exact same response for every message from the
    # SDK in this test: a 200 with an empty JSON object.
    def test_monitor(self):
        logs = [
            "Beginning machine learning...",
            "Still training...",
            "Done!",
        ]

        with patch('sys.stdout', new=StringIO()) as fake_out:
            @monitor("test_job", use_http=True)
            def test_job():
                for log in logs:
                    print(log)
                    time.sleep(2)

            test_job()
            captured_out = fake_out.getvalue()
            for log in logs:
                assert log in captured_out
            assert "error" not in captured_out
            