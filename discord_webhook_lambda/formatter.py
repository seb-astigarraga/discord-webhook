from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

STATE_COLORS: Dict[str, int] = {
    "OK": 0x2ECC71,  # green
    "ALARM": 0xE74C3C,  # red
    "INSUFFICIENT_DATA": 0xF1C40F,  # yellow
}

STATE_EMOJIS: Dict[str, str] = {
    "OK": "✅",
    "ALARM": "🚨",
    "INSUFFICIENT_DATA": "⚠️",
}


def try_parse_json(message: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(message)
        if isinstance(parsed, dict):
            return parsed
        return None
    except json.JSONDecodeError:
        return None


def build_console_alarm_url(
    region: Optional[str], alarm_name: Optional[str]
) -> Optional[str]:
    if not region or not alarm_name:
        return None
    encoded_name = urllib.parse.quote(alarm_name, safe="")
    return f"https://console.aws.amazon.com/cloudwatch/home?region={region}#alarmsV2:alarm/{encoded_name}"


def _extract_metric(trigger: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    # Returns (namespace, metric_name)
    namespace = trigger.get("Namespace")
    metric_name = trigger.get("MetricName")
    if metric_name and not namespace:
        # For composite or anomaly detection, metric info may be nested
        namespace = (
            trigger.get("Metrics", [{}])[0]
            .get("MetricStat", {})
            .get("Metric", {})
            .get("Namespace")
        )
        metric_name = (
            trigger.get("Metrics", [{}])[0]
            .get("MetricStat", {})
            .get("Metric", {})
            .get("MetricName")
        )
    return namespace, metric_name


def _extract_dimensions(trigger: Dict[str, Any]) -> List[str]:
    dims = trigger.get("Dimensions") or []
    if isinstance(dims, list):
        return [
            f"{d.get('name') or d.get('Name')}={d.get('value') or d.get('Value')}"
            for d in dims
            if isinstance(d, dict)
        ]
    return []


def format_cloudwatch_alarm_to_embed(alarm: Dict[str, Any]) -> Dict[str, Any]:
    alarm_name = alarm.get("AlarmName")
    state_value = alarm.get("NewStateValue")
    state_reason = alarm.get("NewStateReason")
    region = alarm.get("Region")
    change_time = alarm.get("StateChangeTime")
    trigger = alarm.get("Trigger") or {}

    namespace, metric_name = _extract_metric(trigger)
    dimensions = _extract_dimensions(trigger)
    color = STATE_COLORS.get(str(state_value).upper(), 0x95A5A6)  # default gray
    console_url = build_console_alarm_url(region, alarm_name)

    # Build concise title with emoji and alarm name; link via embed url
    emoji_for_state = (
        STATE_EMOJIS.get(str(state_value).upper()) if state_value else None
    )
    title_name = str(alarm_name) if alarm_name else "CloudWatch Alarm"
    title = f"{emoji_for_state} {title_name}" if emoji_for_state else title_name

    fields: List[Dict[str, Any]] = []
    if state_value:
        state_text = str(state_value)
        fields.append({"name": "State", "value": state_text, "inline": True})
    if region:
        fields.append({"name": "Region", "value": str(region), "inline": True})
    if metric_name:
        fields.append({"name": "Metric", "value": str(metric_name), "inline": True})
    if namespace:
        fields.append({"name": "Namespace", "value": str(namespace), "inline": True})
    if dimensions:
        fields.append(
            {"name": "Dimensions", "value": ", ".join(dimensions), "inline": False}
        )

    embed: Dict[str, Any] = {
        "title": title,
        "description": state_reason or "",
        "color": color,
    }
    if console_url:
        embed["url"] = console_url
    if change_time:
        embed["timestamp"] = change_time
    if fields:
        embed["fields"] = fields

    return embed


def format_sns_message_to_discord(message: str) -> Dict[str, Any]:
    parsed = try_parse_json(message)
    if parsed is None:
        # Fallback: simple text message
        return {"content": message[:2000]}

    embed = format_cloudwatch_alarm_to_embed(parsed)
    return {"embeds": [embed]}
