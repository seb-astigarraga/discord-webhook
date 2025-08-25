# Discord Webhook for AWS CloudWatch Alarms (Lambda, Python 3.12)

This project contains an AWS Lambda function that receives CloudWatch alarm notifications from SNS and forwards them to a Discord webhook as a rich embed.

## Features

- Parses CloudWatch Alarm SNS messages and formats Discord embeds
- Robust HTTP client with timeouts and exponential backoff retries
- Minimal dependencies (httpx)
- Packaged for AWS SAM deployment

## Requirements

- Python 3.12
- AWS SAM CLI
- An existing SNS Topic that receives CloudWatch Alarm notifications
- A Discord Webhook URL

## Local Dev Setup

```bash
cd /Users/sebas-astigarraga/Documents/github/discord-webhook
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Deployment (AWS SAM)

1. Build

```bash
sam build
```

2. Deploy (guided first time)

```bash
sam deploy --guided
```

Provide the parameters when prompted:

- DiscordWebhookUrl: your Discord webhook URL
- SnsTopicArn: ARN of the SNS topic that receives CloudWatch alarms

Subsequent deploys can use:

```bash
sam deploy
```

## Configuration

- Environment variable `DISCORD_WEBHOOK_URL` must be set (SAM template wires this via parameter).

## Project Layout

```
discord_webhook_lambda/
  handler.py            # AWS Lambda entrypoint
  discord_client.py     # HTTP client for Discord webhook
  formatter.py          # CloudWatch message → Discord Embed
requirements.txt        # Used by SAM to vendor deps inside the Lambda
pyproject.toml          # Dev dependencies and metadata
template.yaml           # SAM template
```

## Manual verification

You can test end-to-end without unit tests:

1. Set the environment variable and invoke the handler locally:

```python
from discord_webhook_lambda.handler import lambda_handler
import os

os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/..."

# Plain text message
lambda_handler({"message": "Hello from Lambda"}, None)

# CloudWatch Alarm JSON (minimal example)
lambda_handler({
  "Records": [
    {"Sns": {"Message": '{"AlarmName":"TestAlarm","NewStateValue":"OK","Region":"us-east-1","StateChangeTime":"2024-01-01T00:00:00Z","NewStateReason":"Example reason"}'}}
  ]
}, None)
```

2. Or deploy with SAM and publish a test message to the created SNS Topic using the AWS Console or CLI.

## License

MIT
