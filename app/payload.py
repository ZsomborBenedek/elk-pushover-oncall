from functools import reduce
from pydantic import BaseModel
import json


class Payload(BaseModel):
    title: str
    alerts: str

    def flatten_dicts_to_string(self, list_of_dicts, indent=""):
        result_string = ""

        for index, dictionary in enumerate(list_of_dicts):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    # Recursively flatten nested dictionaries
                    nested_result = self.flatten_dicts_to_string([value], indent + "  ")
                    result_string += f"{indent}<b>{key}</b>:\n{nested_result}"
                else:
                    result_string += f"{indent}<b>{key}</b>: {value}\n"

            # Add double newline after each original list item except for the last one
            if index < len(list_of_dicts) - 1:
                result_string += "\n"

        return result_string

    def parse_payload(self, included_fields):
        alerts = json.loads(f"[{self.alerts}]")

        filtered_alerts = [
            self.filter_dict(alert, included_keys=included_fields) for alert in alerts
        ]

        alerts_string = self.flatten_dicts_to_string(filtered_alerts)

        return {"title": self.title, "message": alerts_string}

    def filter_dict(self, input_dict: dict, included_keys: list[str]):
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
            output_dict[included_key] = self.deep_get(input_dict, included_key)

        return output_dict

    def deep_get(self, dictionary, keys, default=None):
        return reduce(
            lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
            keys.split("."),
            dictionary,
        )
