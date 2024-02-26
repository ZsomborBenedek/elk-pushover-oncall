from functools import reduce
from logging.handlers import RotatingFileHandler
import os
import time
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import json
import logging
from fastapi.logger import logger as fastapi_logger
import requests


retry_interval = int(os.environ.get("RETRY_INTERVAL", 30))
user_timeout = int(os.environ.get("USER_TIMEOUT", 300))
pushover_credentials = {
    "token": os.environ.get("PUSHOVER_TOKEN"),
    "user": os.environ.get("PUSHOVER_USER"),
}

included_fields = str(os.environ.get("INCLUDED_FIELDS")).split(",")

devices = str(os.environ.get("DEVICES")).split(",")
default_device = str(os.environ.get("DEFAULT_DEVICE"))

MAX_BYTES = 10000000
BACKUP_COUNT = 9


logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.INFO)

log_format = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')

info_handler = RotatingFileHandler(
    'info.log', maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
info_handler.setFormatter(log_format)
info_handler.setLevel(logging.INFO)
logger.addHandler(info_handler)

error_handler = RotatingFileHandler(
    'error.log', maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
error_handler.setFormatter(log_format)
error_handler.setLevel(logging.ERROR)
logger.addHandler(error_handler)

fastapi_logger.handlers = logger.handlers


app = FastAPI()


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
                result_string += f"{indent}<b>{key}</b>:\n{nested_result}"
            else:
                result_string += f"{indent}<b>{key}</b>: {value}\n"

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


def parse_payload(payload: Payload):
    alerts = json.loads(f"[{payload.alerts}]")

    filtered_alerts = [filter_dict(
        alert, included_keys=included_fields) for alert in alerts]

    alerts_string = flatten_dicts_to_string(filtered_alerts)

    return {
        "title": payload.title,
        "message": alerts_string
    }


def send_message(alert_data: dict, device: str, retry: int, expire: int) -> str:
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": pushover_credentials["token"],
        "user": pushover_credentials["user"],
        "device": device,
        "title": alert_data["title"],
        "message": alert_data["message"],
        "html": 1,
        "priority": 2,
        "retry": retry,
        "expire": expire
    }

    response = requests.post(url, data)
    response.raise_for_status()

    return response.json()["receipt"]


def is_acknowledged(receipt: str, token) -> bool:
    url = f"https://api.pushover.net/1/receipts/{receipt}.json?token={token}"

    response = requests.get(url)
    data = response.json()

    return True if data["acknowledged"] == 1 else False


def alert_process(payload: Payload):
    try:
        alert_data = parse_payload(payload)

        logger.info(f"Received alert with data: {alert_data}")

        for id, device in enumerate(devices):
            receipt = send_message(
                alert_data, device, retry_interval, user_timeout)

            logger.info(
                f"Sent notification to {device}, trying next device in {user_timeout} seconds")

            # Sleep for the specified user timeout plus a buffer
            time.sleep(user_timeout + 10)

            acknowledged = is_acknowledged(
                receipt, pushover_credentials["token"])

            if acknowledged:
                logger.info(f"Message acknowledged by {device}")
                return
            else:
                logger.error(f"Message not acknowledged: {alert_data}")
                raise TimeoutError("Nobody acknowledged the notification")
    except TimeoutError as e:
        send_message(
            {"title": e.args[0], "message": "Please check Kibana"}, default_device, retry_interval, user_timeout)
    except Exception as e:
        send_message(
            {"title": e.args[0], "message": "Please check Kibana"}, default_device, retry_interval, user_timeout)
        logger.error(str(e))


@app.post("/")
async def post_alert(payload: Payload, background_tasks: BackgroundTasks):
    background_tasks.add_task(alert_process, payload)
    return {"message": "Alert added to queue"}


if __name__ != "__main__":
    fastapi_logger.setLevel(logger.level)
else:
    fastapi_logger.setLevel(logging.DEBUG)
