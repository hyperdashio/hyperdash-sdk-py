# -*- coding: utf-8 -*-

import json
import os
import random
import string
import time

from six import StringIO
from six import PY2
from mock import patch
from nose.tools import assert_in
import requests

from hyperdash import monitor
from mocks import init_mock_server
from hyperdash.constants import get_hyperdash_logs_home_path_for_job
from threading import Thread
from hyperdash.constants import MAX_LOG_SIZE_BYTES
from hyperdash.hyper_dash import HyperDash

server_sdk_messages = []


class TestSDK(object):
    def setup(self):
        global server_sdk_messages
        server_sdk_messages = []

    @classmethod
    def setup_class(_cls):
        request_handle_dict = init_mock_server()

        def sdk_message(response):
            global server_sdk_messages
            message = json.loads(response.rfile.read(
                int(response.headers['Content-Length'])))
            server_sdk_messages.append(message)

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

        request_handle_dict[("POST", "/api/v1/sdk/http")] = sdk_message

    def test_monitor(self):
        job_name = "some:job(name)with unsafe for files ystem chars"
        logs = [
            "Beginning machine learning...",
            "Still training...",
            "Done!",
            # Handle unicode
            "字",
            # Huge log,
            ''.join(random.choice(string.lowercase)
                    for x in range(10 * MAX_LOG_SIZE_BYTES))
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

    def test_monitor_with_hd_client_and_no_capture_io(self):
        job_name = "some_job_name"

        with patch('sys.stdout', new=StringIO()) as fake_out:
            def worker(thread_num, monitored):
                @monitor(job_name, capture_io=False)
                def monitored_func(hd_client):
                    print("this should not be in there")
                    hd_client.logger.info(thread_num)
                    hd_client.logger.info(
                        "thread {} is doing some work".format(thread_num))
                    hd_client.logger.info("字")
                    time.sleep(1)
                return monitored_func

            t1 = Thread(target=worker(1, True))
            t2 = Thread(target=worker(2, True))
            t3 = Thread(target=worker(3, True))

            t1.daemon = True
            t2.daemon = True
            t3.daemon = True

            t1.start()
            t2.start()
            t3.start()

            t1.join()
            t2.join()
            t3.join()

        # Make sure logs were persisted -- We use this as a proxy
        # to make sure that each of the threads only captured its
        # own output by checkign that each log file only has 5
        # lines
        log_dir = get_hyperdash_logs_home_path_for_job(job_name)
        latest_log_files = sorted([
            os.path.join(log_dir, filename) for
            filename in
            os.listdir(log_dir)
        ], key=os.path.getmtime)[-3:]
        for file_name in latest_log_files:
            with open(file_name, 'r') as log_file:
                data = log_file.read()
                assert "this should not be in there" not in data
                assert "is doing some work" in data
                assert "字" in data
                assert (len(data.split("\n")) == 5)
            os.remove(file_name)
