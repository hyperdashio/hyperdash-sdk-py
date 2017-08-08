# -*- coding: utf-8 -*-
import json
import os
import time

from six import StringIO
from six import PY2
from mock import patch
from nose.tools import assert_in
import requests

from hyperdash import monitor
from mocks import init_mock_server
from hyperdash.constants import get_hyperdash_logs_home_path_for_job

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

            # Add response content. In this case, we use the exact same response for
            # all messages from the SDK because the current implementation ignores the
            # body of the response unless there is an error.
            response_content = json.dumps({})

            response.wfile.write(response_content.encode('utf-8'))

        request_handle_dict[("POST", "/api/v1/sdk/http")] = sdk_message

    def test_monitor(self):
        job_name = "some:job(name)with unsafe for files ystem chars"
        logs = [
            "Beginning machine learning...",
            "Still training...",
            "Done!",
            # Handle unicode
            "字",
        ]
        test_obj = {'some_obj_key': 'some_value'}
        expected_return = "final_result"

        with patch('sys.stdout', new=StringIO()) as fake_out:
            @monitor(job_name)
            def test_job():
                for log in logs:
                    print(log)
                    time.sleep(2)
                print(test_obj)
                time.sleep(2)
                return expected_return

            return_val = test_job()

            assert return_val == expected_return
            captured_out = fake_out.getvalue()
            for log in logs:
                if PY2:
                    assert log in captured_out.encode("utf-8")
                    continue
                assert log in captured_out
            assert str(test_obj) in captured_out            

            assert "error" not in captured_out
        
        # Make sure logs were persisted
        log_dir = get_hyperdash_logs_home_path_for_job(job_name)
        latest_log_file = max([
            os.path.join(log_dir, filename) for
            filename in
            os.listdir(log_dir)
        ], key=os.path.getmtime)
        with open(latest_log_file, 'r') as log_file:
            data = log_file.read()
            for log in logs:
                assert_in(log, data)
        os.remove(latest_log_file)

    def test_monitor_raises_exceptions(self):
        exception_raised = True
        expected_exception = "some_exception"

        @monitor("test_job")
        def test_job():
            time.sleep(2)
            raise Exception(expected_exception)

        try:
            test_job()
            exception_raised = False
        except Exception as e:
            assert str(e) == expected_exception
        
        assert exception_raised
