import requests


class Alerter:
    token: str
    user: str
    retry: int
    expire: int

    def __init__(self, pushover_credentials: dict, retry: int, expire: int):
        self.token = pushover_credentials["token"]
        self.user = pushover_credentials["user"]
        self.retry = retry
        self.expire = expire

    def send_message(self, alert_data: dict, device: str) -> str:
        url = "https://api.pushover.net/1/messages.json"

        data = {
            "token": self.token,
            "user": self.user,
            "title": alert_data["title"],
            "message": alert_data["message"],
            "device": device,
            "html": 1,
            "priority": 2,
            "retry": self.retry,
            "expire": self.expire,
        }

        response = requests.post(url, data)
        response.raise_for_status()

        return response.json()["receipt"]

    def is_acknowledged(self, receipt: str, token: str) -> bool:
        url = f"https://api.pushover.net/1/receipts/{receipt}.json?token={token}"

        response = requests.get(url)
        data = response.json()

        return True if data["acknowledged"] == 1 else False
