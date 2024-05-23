from functools import reduce
from pydantic import BaseModel
import json


class Payload:
    title: str

    def flatten_dict(self, dictionary: dict, indent=""):
        result_string = ""
        for key, value in dictionary.items():
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                nested_result = self.flatten_dict(value, indent + "  ")
                result_string += f"{indent}<b>{key}</b>:\n{nested_result}"
            else:
                result_string += f"{indent}<b>{key}</b>: {value}\n"

        return result_string

    def flatten_list_of_dicts(self, list_of_dicts: list[dict], indent=""):
        result_string = ""

        for index, dictionary in enumerate(list_of_dicts):
            result_string += self.flatten_dict(dictionary, indent)
            # Add double newline after each original list item except for the last one
            if index < len(list_of_dicts) - 1:
                result_string += "\n"

        return result_string

    def filter_dict(self, input_dict: dict, included_keys: list[str]) -> dict:
        output_dict = {}
        for included_key in included_keys:
            output_dict[included_key] = self.deep_get(
                input_dict, included_key, default="-"
            )

        return output_dict

    def deep_get(self, dictionary, keys, default):
        return reduce(
            lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
            keys.split("."),
            dictionary,
        )


class ElasticPayload(BaseModel, Payload):
    alerts: str

    def parse_payload(self, included_fields):
        alerts = json.loads(f"[{self.alerts}]")
        filtered_alerts = [
            self.filter_dict(alert, included_keys=included_fields) for alert in alerts
        ]
        alerts_string = self.flatten_list_of_dicts(filtered_alerts)

        return {"title": self.title, "message": alerts_string}


class PraecoPayload(Payload):
    alert: dict

    def __init__(self, title: str, alert: dict) -> None:
        super().__init__()
        self.title = alert[title]
        self.alert = alert

    def parse_payload(self, message_fields: list[str]):
        filtered_alert = self.filter_dict(self.alert, included_keys=message_fields)
        alert_string = self.flatten_dict(filtered_alert)

        return {"title": self.title, "message": alert_string}

    def deep_get(self, dictionary, key: str, default):
        return dictionary.get(key, default)
