from functools import reduce
from fastapi import FastAPI
from pydantic import BaseModel
import json
import logging
from fastapi.logger import logger as fastapi_logger

gunicorn_error_logger = logging.getLogger("gunicorn.error")
gunicorn_logger = logging.getLogger("gunicorn")
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = gunicorn_error_logger.handlers

fastapi_logger.handlers = gunicorn_error_logger.handlers

included_fields = [
    "@timestamp", "related", "signal.reason", "kibana.alert.rule.risk_score", "kibana.alert.rule.severity"
]


app = FastAPI()

if __name__ != "__main__":
    fastapi_logger.setLevel(gunicorn_logger.level)
else:
    fastapi_logger.setLevel(logging.DEBUG)


class Payload(BaseModel):
    title: str
    alerts: str


def flatten_dicts_to_string(list_of_dicts, indent=''):
    result_string = ''

    for index, dictionary in enumerate(list_of_dicts):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                nested_result = flatten_dicts_to_string([value], indent + '  ')
                result_string += f"{indent}{key}:\n{nested_result}"
            else:
                result_string += f"{indent}{key}: {value}\n"

        # Add double newline after each original list item except for the last one
        if index < len(list_of_dicts) - 1:
            result_string += '\n'

    return result_string


def filter_dict(input_dict: dict, included_keys: list[str]):
    """
    Filters a dictionary to include only specified key-value pairs.

    Args:
        input_dict (dict): The input dictionary.
        included_keys (set): Set of keys to include in the dictionary.

    Returns:
        dict: Dictionary with only the specified key-value pairs.
    """
    output_dict = {}

    for included_key in included_keys:
        output_dict[included_key] = deep_get(input_dict, included_key)

    return output_dict


def deep_get(dictionary, keys, default=None):
    return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary)


@app.post("/")
def post_alert(payload: Payload):

    alerts = json.loads(f"[{payload.alerts}]")

    filtered_alerts = [filter_dict(
        alert, included_keys=included_fields) for alert in alerts]

    alerts_string = flatten_dicts_to_string(filtered_alerts)

    pushover_data = {
        "title": payload.title,
        "alerts": alerts_string
    }

    print(json.dumps(pushover_data))

    return pushover_data
