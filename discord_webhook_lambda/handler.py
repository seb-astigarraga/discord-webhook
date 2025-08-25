from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .discord_client import DiscordClient
from .formatter import format_sns_message_to_discord


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    return value


def lambda_handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:  # pragma: no cover - signature required by AWS
    webhook_url = _get_env("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    client = DiscordClient(webhook_url=webhook_url)

    records: List[Dict[str, Any]] = (
        event.get("Records", []) if isinstance(event, dict) else []
    )
    delivered = 0

    if not records:
        # Allow direct invocation with a single message string
        message = event.get("message") if isinstance(event, dict) else None
        if isinstance(message, str):
            payload = format_sns_message_to_discord(message)
            client.send(content=payload.get("content"), embeds=payload.get("embeds"))
            delivered += 1
    else:
        for record in records:
            sns = record.get("Sns") if isinstance(record, dict) else None
            message = sns.get("Message") if isinstance(sns, dict) else None
            if isinstance(message, str):
                payload = format_sns_message_to_discord(message)
                client.send(
                    content=payload.get("content"), embeds=payload.get("embeds")
                )
                delivered += 1

    return {"delivered": delivered}
