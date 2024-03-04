# Alerthandler

This utility can handle incoming json REST API calls and forward them to Pushover. Tested with Elastic Security.


## How it works

1. REST api POST to https://localhost:8444
2. Alerthandler Docker container transforms data
3. Submit alert to Pushover message api (https://pushover.net/api) 
	1. Response: receipt
4. Check acknowledgement via Pushover receipt api (https://pushover.net/api/receipts)
5. If not acknowledged in 5 mins, go to next device

---

Configurations can be made in the `.env` file:

```dotenv
PUSHOVER_TOKEN=*****
PUSHOVER_USER=*****

RETRY_INTERVAL=30
USER_TIMEOUT=300

INCLUDED_FIELDS=@timestamp,related,kibana.alert.rule.risk_score,kibana.alert.rule.severity,signal.reason,signal.rule.description

DEVICES=zsombor-phone,zsombor-phone,zsombor-phone
DEFAULT_DEVICE=zsombor-phone
ITERATION_COUNT=3
```

From the `/opt/alerthandler` directory:

```bash
docker compose up --build -d
```

---

## Create self-signed certificate and key

```sh
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx/certs/server.key -out nginx/certs/server.crt
```

---
## ELK test rule: Sudo test

- Elastic Security notifcation action: Webhook
- Action frequency: For each alert (time sensitive) or Summary (e.g. morning report)
- Webhook body:

```json
{
    "title": "{{rule.name}} - severity: {{context.rule.severity}}",
    "alerts": "{{context.alerts}}"
}
```

---
### Submitting an alert to Pushover: 

```curl
curl --request POST \
  --url 'https://api.pushover.net/1/messages.json?=' \
  --header 'Content-Type: application/json' \
  --header 'User-Agent: insomnia/8.6.0' \
  --data '{
	"token": "*****",
	"user": "*****",
	"device": "*****",
	"priority": 2,
	"retry": 30,
	"expire": 60,
	"title": "Test Rule - severity: 1",
	"message": "This is just a test."
}'
```

#### Response

```json
{

      "receipt": "*****",
      "status": 1,
      "request": "*****"
}
```

---
#### Check if an alert has been acknowledged:

```curl
curl --request GET \
  --url 'https://api.pushover.net/1/receipts/*****.json?token=*****' \
  --header 'User-Agent: insomnia/8.6.0'
  ```
### Response:

```json
{
      "status": 1,
      "acknowledged": 0,
      "acknowledged_at": 0,
      "acknowledged_by": "",
      "acknowledged_by_device": "",
      "last_delivered_at": 1707164965,
      "expired": 1,
      "expires_at": 1707164995,
      "called_back": 0,
      "called_back_at": 0,
      "request": "*****"
}
```
