from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Any, Dict, List, Optional

import json
import urllib.request
import urllib.error


@dataclass(slots=True)
class DiscordClient:
    webhook_url: str
    timeout_seconds: float = 10.0
    max_retries: int = 3
    backoff_seconds: float = 0.6

    def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        payload: Dict[str, Any] = {}
        if content:
            payload["content"] = content[:2000]
        if embeds:
            # Discord allows up to 10 embeds per message
            payload["embeds"] = embeds[:10]

        if not payload.get("content") and not payload.get("embeds"):
            # Nothing to send
            return

        self._post_with_retries(payload)

    def _post_with_retries(self, payload: Dict[str, Any]) -> None:
        attempt: int = 0
        last_error: Optional[BaseException] = None
        while attempt <= self.max_retries:
            try:
                request = urllib.request.Request(
                    self.webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        # Some CDNs in front of Discord reject requests without a UA
                        "User-Agent": "DiscordWebhookLambda/1.0 (+https://github.com/)",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(
                    request, timeout=self.timeout_seconds
                ) as resp:
                    status_code = resp.getcode()
                    # Retry on rate limit or server error
                    if status_code == 429:
                        retry_after_header = resp.headers.get("Retry-After")
                        delay = (
                            float(retry_after_header)
                            if retry_after_header is not None
                            else (self.backoff_seconds * (2**attempt))
                        )
                        sleep(max(0.0, delay))
                        attempt += 1
                        continue
                    if 500 <= status_code < 600:
                        attempt += 1
                        sleep(self.backoff_seconds * (2 ** (attempt - 1)))
                        continue
                    # For 2xx and 4xx (except 429), stop. 4xx means permanent error
                    if 200 <= status_code < 300:
                        return
                    if 400 <= status_code < 500:
                        raise urllib.error.HTTPError(
                            self.webhook_url,
                            status_code,
                            "Client error",
                            resp.headers,
                            None,
                        )
                    # Any other unexpected status
                    raise RuntimeError(f"Unexpected HTTP status: {status_code}")
            except urllib.error.HTTPError as exc:
                # Handle HTTP errors specifically
                if exc.code == 429:
                    retry_after_header = None
                    if exc.headers is not None:
                        retry_after_header = exc.headers.get("Retry-After")
                    delay = (
                        float(retry_after_header)
                        if retry_after_header is not None
                        else (self.backoff_seconds * (2**attempt))
                    )
                    sleep(max(0.0, delay))
                    attempt += 1
                    continue
                if 500 <= exc.code < 600:
                    last_error = exc
                    attempt += 1
                    if attempt > self.max_retries:
                        break
                    sleep(self.backoff_seconds * (2 ** (attempt - 1)))
                    continue
                # 4xx (except 429): do not retry
                error_body: str = ""
                try:
                    error_body = exc.read().decode("utf-8", "ignore")
                except Exception:
                    # If we can't read the body, proceed without it
                    pass
                # Include body to aid troubleshooting (e.g., Discord may return JSON describing the error)
                raise RuntimeError(
                    f"Discord webhook request failed with {exc.code} {exc.reason}. "
                    f"Body: {error_body[:500]}"
                )
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                attempt += 1
                if attempt > self.max_retries:
                    break
                sleep(self.backoff_seconds * (2 ** (attempt - 1)))
            except Exception as exc:  # pragma: no cover - unexpected errors
                # Do not retry on unexpected exceptions by default
                raise exc
        if last_error:
            raise last_error
