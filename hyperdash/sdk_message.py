import json
import time
import uuid


TYPE_LOG = 'log'
TYPE_STARTED = 'run_started'
TYPE_ENDED = 'run_ended'
TYPE_HEARTBEAT = 'heartbeat'


def create_log_message(sdk_run_uuid, level, body):
    return create_sdk_message(
        sdk_run_uuid,
        TYPE_LOG,
        {
            'uuid': str(uuid.uuid4()),
            'level': level,
            'body': body,
        }
    )


def create_run_started_message(sdk_run_uuid, job_name):
    return create_sdk_message(
        sdk_run_uuid,
        TYPE_STARTED,
        {
            'job_name': job_name,
        },
    )


def create_run_ended_message(sdk_run_uuid, final_status):
    return create_sdk_message(
        sdk_run_uuid,
        TYPE_ENDED,
        {'final_status': final_status},
    )


def create_heartbeat_message(sdk_run_uuid):
  return create_sdk_message(sdk_run_uuid, TYPE_HEARTBEAT, {})


def create_sdk_message(sdk_run_uuid, typeStr, payload):
  """Create a structured message for the server."""
  return json.dumps({
      'type': typeStr,
      'timestamp': int(time.time() * 1000),
      'sdk_run_uuid': sdk_run_uuid,
      'payload': payload,
  })
