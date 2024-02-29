from logging.handlers import RotatingFileHandler
import os
import time
from fastapi import FastAPI, BackgroundTasks
import logging
from fastapi.logger import logger as fastapi_logger
import requests
from alerter import Alerter
from payload import Payload


RETRY_INTERVAL = int(os.environ.get("RETRY_INTERVAL", 30))
USER_TIMEOUT = int(os.environ.get("USER_TIMEOUT", 300))
PUSHOVER_CREDENTIALS = {
    "token": os.environ.get("PUSHOVER_TOKEN"),
    "user": os.environ.get("PUSHOVER_USER"),
}

INCLUDED_FIELDS = str(os.environ.get("INCLUDED_FIELDS")).split(",")

DEVICES = str(os.environ.get("DEVICES")).split(",")
DEFAULT_DEVICE = str(os.environ.get("DEFAULT_DEVICE"))

MAX_BYTES = 10000000
BACKUP_COUNT = 9


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

log_format = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")

info_handler = RotatingFileHandler(
    "info.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
)
info_handler.setFormatter(log_format)
info_handler.setLevel(logging.INFO)
logger.addHandler(info_handler)

error_handler = RotatingFileHandler(
    "error.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
)
error_handler.setFormatter(log_format)
error_handler.setLevel(logging.ERROR)
logger.addHandler(error_handler)

fastapi_logger.handlers = logger.handlers


app = FastAPI()


def is_acknowledged(receipt: str, token) -> bool:
    url = f"https://api.pushover.net/1/receipts/{receipt}.json?token={token}"

    response = requests.get(url)
    data = response.json()

    return True if data["acknowledged"] == 1 else False


def alert_process(payload: Payload):
    try:
        alert_data = payload.parse_payload(INCLUDED_FIELDS)
        alert = Alerter(PUSHOVER_CREDENTIALS, RETRY_INTERVAL, USER_TIMEOUT)

        logger.info(f"Received alert with data: {alert_data}")

        for id, device in enumerate(DEVICES):
            receipt = alert.send_message(alert_data, device)

            logger.info(
                f"Sent notification to {device}, trying next device in {USER_TIMEOUT} seconds"
            )

            # Sleep for the specified user timeout plus a buffer
            time.sleep(USER_TIMEOUT + 10)

            acknowledged = is_acknowledged(receipt, PUSHOVER_CREDENTIALS["token"])

            if acknowledged:
                logger.info(f"Message acknowledged by {device}")
                return
            else:
                logger.error(f"Message not acknowledged by {device}")
        else:
            raise TimeoutError("Nobody acknowledged the notification")
    except TimeoutError as e:
        alert.send_message(
            {"title": "Please check Kibana", "message": e.args[0]}, DEFAULT_DEVICE
        )
    except Exception as e:
        alert.send_message(
            {"title": "Please check Alerthandler", "message": e.args[0]},
            DEFAULT_DEVICE,
        )
        logger.error(str(e))


@app.post("/")
async def post_alert(payload: Payload, background_tasks: BackgroundTasks):
    background_tasks.add_task(alert_process, payload)
    return {"message": "Alert added to queue"}


if __name__ != "__main__":
    fastapi_logger.setLevel(logger.level)
else:
    fastapi_logger.setLevel(logging.DEBUG)
