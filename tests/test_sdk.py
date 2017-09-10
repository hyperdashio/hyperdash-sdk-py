# -*- coding: utf-8 -*-

import json
import os
import random
import string
import time

import six
from six import StringIO
from six import PY2
from mock import patch
from nose.tools import assert_in
import requests

from hyperdash import monitor
from hyperdash import Experiment
from mocks import init_mock_server
from hyperdash.constants import get_hyperdash_logs_home_path_for_job
from threading import Thread
from hyperdash.constants import MAX_LOG_SIZE_BYTES
from hyperdash.hyper_dash import HyperDash

server_sdk_messages = []

if PY2:
    lowercase_letters = string.lowercase
else:
    lowercase_letters = string.ascii_lowercase


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
                int(response.headers["Content-Length"])).decode("utf-8"))

            server_sdk_messages.append(message)

            # Add response status code.
            response.send_response(requests.codes.ok)

            # Add response headers.
            response.send_header(
                "Content-Type", "application/json; charset=utf-8")
            response.end_headers()

            # Add response content. In this case, we use the exact same response for
            # all messages from the SDK because the current implementation ignores the
            # body of the response unless there is an error.
            response_content = json.dumps({})

            response.wfile.write(response_content.encode("utf-8"))

        request_handle_dict[("POST", "/api/v1/sdk/http")] = sdk_message

    def test_monitor(self):
        job_name = "some:job(name)with unsafe for files ystem chars"
        logs = [
            "Beginning machine learning...",
            "Still training...",
            "Done!",
            # Handle unicode
            "字",
            # Huge log
            "".join(random.choice(lowercase_letters)
                    for x in range(10 * MAX_LOG_SIZE_BYTES)),
        ]
        test_obj = {"some_obj_key": "some_value"}
        expected_return = "final_result"

        with patch("sys.stdout", new=StringIO()) as fake_out:
            @monitor(job_name)
            def test_job():
                for log in logs:
                    print(log)
                    time.sleep(0.1)
                print(test_obj)
                time.sleep(0.1)
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
        with open(latest_log_file, "r") as log_file:
            data = log_file.read()
            for log in logs:
                assert_in(log, data)
        os.remove(latest_log_file)

    def test_monitor_raises_exceptions(self):
        exception_raised = True
        expected_exception = "some_exception"

        @monitor("test_job")
        def test_job():
            time.sleep(0.1)
            raise Exception(expected_exception)

        try:
            test_job()
            exception_raised = False
        except Exception as e:
            assert str(e) == expected_exception

        assert exception_raised

    def test_monitor_with_hd_client_and_no_capture_io(self):
        job_name = "some_job_name"

        with patch("sys.stdout", new=StringIO()):
            def worker(thread_num):
                @monitor(job_name, capture_io=False)
                def monitored_func(hd_client):
                    print("this should not be in there")
                    hd_client.logger.info(thread_num)
                    hd_client.logger.info(
                        "thread {} is doing some work".format(thread_num))
                    hd_client.logger.info("字")
                    time.sleep(0.1)
                return monitored_func

            t1 = Thread(target=worker(1))
            t2 = Thread(target=worker(2))
            t3 = Thread(target=worker(3))

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
            with open(file_name, "r") as log_file:
                data = log_file.read()
                assert "this should not be in there" not in data
                assert "is doing some work" in data
                assert "字" in data
                assert (len(data.split("\n")) == 5)
            os.remove(file_name)

    def test_monitor_limits_server_message_size(self):
        job_name = "some_job_name"
        logs = [
            "Beginning machine learning...",
            "Still training...",
            "Done!",
            # Handle unicode
            "字",
            # Huge log
            "".join(random.choice(lowercase_letters)
                    for x in range(10 * MAX_LOG_SIZE_BYTES)),
        ]
        test_obj = {"some_obj_key": "some_value"}
        expected_return = "final_result"

        @monitor(job_name)
        def test_job():
            for log in logs:
                print(log)
                time.sleep(0.1)
            print(test_obj)
            time.sleep(0.1)
            return expected_return

        return_val = test_job()

        assert return_val == expected_return

        all_text_sent_to_server = ""
        for msg in server_sdk_messages:
            payload = msg["payload"]
            if "body" in payload:
                all_text_sent_to_server = all_text_sent_to_server + \
                    payload["body"]

        for log in logs:
            if PY2:
                assert log in all_text_sent_to_server.encode("utf-8")
                continue
            assert log in all_text_sent_to_server
        assert str(test_obj) in all_text_sent_to_server

    def test_metric(self):
        job_name = "metric job name"

        metrics = {
            "acc": 99,
            "loss": 0.00000000041,
            "val_loss": 4324320984309284328743827432,
            "mse": -431.321,
        }

        @monitor(job_name)
        def test_job(hd_client):
            for key, val in six.iteritems(metrics):
                hd_client.metric(key, val)
            return

        test_job()

        sent_vals = []
        for msg in server_sdk_messages:
            payload = msg["payload"]
            if "name" in payload:
                sent_vals.append(payload)

        assert len(metrics) == len(sent_vals)
        for pair in sent_vals:
            assert metrics[pair["name"]] == pair["value"]

    def test_param(self):
        params = (("lr", 0.5), ("loss_function", "MSE"))

        # Run a test job that emits some hyperparameters
        with patch("sys.stdout", new=StringIO()) as fake_out:
            @monitor("test params")
            def test_job(hd_client):
                for param in params:
                    hd_client.param(param[0], param[1])
                    time.sleep(0.1)
                return
            test_job()

        # Collect sent SDK messages that had a params payload
        sent_messages = []
        for msg in server_sdk_messages:
            payload = msg["payload"]
            if "params" in payload:
                sent_messages.append(payload)

        # Assert the sent SDK messages are what we expect
        assert len(params) == len(sent_messages)
        for i, message in enumerate(sent_messages):
            name = params[i][0]
            val = params[i][1]
            assert message["params"][name] == val

        # Assert that the appropriate messages were printed to STDOUT
        for param in params:
            assert param[0] in fake_out.getvalue()
            assert str(param[1]) in fake_out.getvalue()

    def test_experiment(self):
        # Run a test job via the Experiment API
        # Make sure log file is where is supposed to be
        # look at decorator
        # verify run start/stop is sent
        with patch("sys.stdout", new=StringIO()) as faked_out:
            exp = Experiment("MNIST")
            exp.log("test print")
            exp.param("batch size", 32)
            for i in exp.iter(2):
                exp.metric("accuracy", i*0.2)
            time.sleep(0.1)
            exp.end()
        
        # Test params match what is expected
        params_messages = []
        for msg in server_sdk_messages:
            payload = msg["payload"]
            if "params" in payload:
                params_messages.append(payload)

        expect_params = [
            {
                "params": {
                    "batch size": 32,
                },
                "is_internal": False,
            },
            {
                "params": {
                    "hd_iter_0_epochs": 2,
                },
                "is_internal": True,
            },
        ]    
        assert len(expect_params) == len(params_messages)
        for i, message in enumerate(params_messages):
            assert message == expect_params[i]

        # Test metrics match what is expected
        metrics_messages = []
        for msg in server_sdk_messages:
            payload = msg["payload"]
            if "name" in payload:
                metrics_messages.append(payload)

        expect_metrics = [
            {"is_internal": True, "name": "hd_iter_0", "value": 0},
            {"is_internal": False, "name": "accuracy", "value": 0},
            {"is_internal": True, "name": "hd_iter_0", "value": 1},
            {"is_internal": False, "name": "accuracy", "value": 0.2},
       ]
        # print(len(expect_metrics), len(metrics_messages))
        print(expect_metrics)
        print(metrics_messages)
        assert len(expect_metrics) == len(metrics_messages)
        for i, message in enumerate(metrics_messages):
            # print(expect_metrics[i])
            assert message == expect_metrics[i]
        
        captured_out = faked_out.getvalue()
        assert "error" not in captured_out
        
        # Make sure logs were persisted
        expect_logs = [
            "{ batch size: 32 }",
            "test print",
            "| Iteration 0 of 1 |",
            "| accuracy:   0.000000 |",
        ]

        log_dir = get_hyperdash_logs_home_path_for_job("MNIST")
        latest_log_file = max([
            os.path.join(log_dir, filename) for
            filename in
            os.listdir(log_dir)
        ], key=os.path.getmtime)
        with open(latest_log_file, "r") as log_file:
            data = log_file.read()
            for log in expect_logs:
                assert_in(log, data)
        os.remove(latest_log_file)
        
    def experiment_raises_exceptions(self):
        exception_raised = True
        expected_exception = "some_exception_b"

        def test_job():
            exp = Experiment("Exception experiment")
            time.sleep(0.1)
            raise Exception(expected_exception)
            exp.end()
        try:
            test_job()
            exception_raised = False
        except Exception as e:
            assert str(e) == expected_exception

        assert exception_raised

    def test_iter(self):
        # Run a test job that includes the iterator function
        with patch("sys.stdout", new=StringIO()) as fake_out:
            @monitor("test iter")
            def test_job(hd_client):
                hd_client.param("user_param", "test")
                for i in hd_client.iter(5):
                    hd_client.metric("loss", i)
                for i in hd_client.iter(3):
                    hd_client.metric("loss", i)
            test_job()

        # Collect sent SDK messages that had a params payload
        param_messages = []
        for msg in server_sdk_messages:
            payload = msg["payload"]
            if "params" in payload:
                param_messages.append(payload)

        # Collect sent SDK messages that had a metrics payload
        metric_messages = []
        for msg in server_sdk_messages:
            payload = msg["payload"]
            if "name" in payload:
                metric_messages.append(payload)

        # Assert the sent param SDK messages are what we expect
        expected_params = [
            {
                "params": {
                    "user_param": "test",
                },
                "is_internal": False,
            },
            {
                "params": {
                    "hd_iter_0_epochs": 5,
                },
                "is_internal": True,
            },
            {
                "params": {
                    "hd_iter_1_epochs": 3,
                },
                "is_internal": True,
            }
        ]
        assert len(expected_params) == len(param_messages)
        for i, message in enumerate(param_messages):
            assert message == expected_params[i]

        # Assert the sent metric SDK messages are what we expect
        expected_metrics = [
            {"is_internal": True, "name": "hd_iter_0", "value": 0},
            {"is_internal": False, "name": "loss", "value": 0},
            {"is_internal": True, "name": "hd_iter_0", "value": 1},
            {"is_internal": False, "name": "loss", "value": 1},
            {"is_internal": True, "name": "hd_iter_0", "value": 2},
            {"is_internal": False, "name": "loss", "value": 2},
            {"is_internal": True, "name": "hd_iter_0", "value": 3},
            {"is_internal": False, "name": "loss", "value": 3},
            {"is_internal": True, "name": "hd_iter_0", "value": 4},
            {"is_internal": False, "name": "loss", "value": 4},
            {"is_internal": True, "name": "hd_iter_1", "value": 0},
            {"is_internal": False, "name": "loss", "value": 0},
            {"is_internal": True, "name": "hd_iter_1", "value": 1},
            {"is_internal": False, "name": "loss", "value": 1},
            {"is_internal": True, "name": "hd_iter_1", "value": 2},
            {"is_internal": False, "name": "loss", "value": 2},
        ]
        # print(len(expected_metrics), len(metric_messages))
        assert len(expected_metrics) == len(metric_messages)
        for i, message in enumerate(metric_messages):
            assert message == expected_metrics[i]

        # Assert that the internal parameters / metrics were not printed to STDOUT
        assert "hd_iter_0" not in fake_out.getvalue()
        assert "hd_iter_1" not in fake_out.getvalue()
        assert "hd_iter_0_epochs" not in fake_out.getvalue()
        assert "hd_iter_1_epochs" not in fake_out.getvalue()
        for i in range(5):
            assert "| Iteration {} of {} |".format(i, 4) in fake_out.getvalue()
        for i in range(3):
            assert "| Iteration {} of {} |".format(i, 2) in fake_out.getvalue()
