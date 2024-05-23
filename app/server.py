import os
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import Union
from fastapi import FastAPI, BackgroundTasks
from fastapi.logger import logger as fastapi_logger
from alerter import Alerter
from payload import ElasticPayload, Payload, PraecoPayload


RETRY_INTERVAL = int(os.environ.get("RETRY_INTERVAL", 30))
USER_TIMEOUT = int(os.environ.get("USER_TIMEOUT", 300))
PUSHOVER_CREDENTIALS = {
    "token": str(os.environ.get("PUSHOVER_TOKEN")),
    "user": str(os.environ.get("PUSHOVER_USER")),
}

INCLUDED_FIELDS = str(os.environ.get("INCLUDED_FIELDS")).split(",")
TITLE_FIELD = str(os.environ.get("TITLE_FIELD"))

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


def alert_process(payload: Payload | dict):
    try:
        alerter = Alerter(PUSHOVER_CREDENTIALS, RETRY_INTERVAL, USER_TIMEOUT)

        if isinstance(payload, ElasticPayload):
            alert_data = payload.parse_payload(INCLUDED_FIELDS)
        elif isinstance(payload, dict):
            pp = PraecoPayload(TITLE_FIELD, payload)
            alert_data = pp.parse_payload(INCLUDED_FIELDS)

        logger.info(f"Received alert with data: {alert_data}")

        for id, device in enumerate(DEVICES):
            receipt = alerter.send_message(alert_data, device)

            logger.info(
                f"Sent notification to {device}, trying next device in {USER_TIMEOUT} seconds"
            )

            # Sleep for the specified user timeout plus a buffer
            time.sleep(USER_TIMEOUT + 10)

            acknowledged = alerter.is_acknowledged(
                receipt, PUSHOVER_CREDENTIALS["token"]
            )

            if acknowledged:
                logger.info(f"Message acknowledged by {device}")
                return
            else:
                logger.error(f"Message not acknowledged by {device}")
        else:
            raise TimeoutError("Nobody acknowledged the notification")
    except TimeoutError as e:
        alerter.send_message(
            {"title": "Please check Kibana", "message": e.args[0]}, DEFAULT_DEVICE
        )
    except Exception as e:
        alerter.send_message(
            {"title": "Please check Alerthandler", "message": e.args[0]},
            DEFAULT_DEVICE,
        )
        logger.error(str(e))


@app.post("/")
async def post_alert(
    payload: Union[ElasticPayload, dict], background_tasks: BackgroundTasks
):
    background_tasks.add_task(alert_process, payload)
    return {"message": "Alert added to queue"}


if __name__ != "__main__":
    fastapi_logger.setLevel(logger.level)
else:
    fastapi_logger.setLevel(logging.DEBUG)
