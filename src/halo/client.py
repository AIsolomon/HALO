"""HTTP boundary: auth, timeouts, bounded read retries, safe Jira errors."""

import asyncio
import math
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from halo.config import Settings
from halo.errors import JiraError


class JiraClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.http = httpx.AsyncClient(
            base_url=settings.jira_base_url,
            auth=httpx.BasicAuth(settings.jira_email, settings.jira_api_token.get_secret_value()),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=httpx.Timeout(settings.halo_timeout_seconds),
            follow_redirects=False,
            trust_env=not settings.halo_demo,
            transport=transport,
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def request(self, method: str, path: str, **kwargs: Any) -> dict:
        # Only fixed API paths assembled by the service may reach this client.
        if not path.startswith("/rest/api/3/") or ".." in path or "?" in path or "#" in path:
            raise ValueError("Expected a Jira REST API v3 path")
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                response = await self.http.request(method, path, **kwargs)
            except httpx.RequestError:
                # Never include request headers, tokens, or raw upstream errors.
                raise JiraError("Jira is unreachable or timed out; check connectivity") from None
            if response.status_code in (429, 502, 503, 504) and attempt + 1 < attempts:
                delay = 0.25 * (2**attempt)
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        try:
                            retry_at = parsedate_to_datetime(retry_after)
                            if retry_at.tzinfo is None:
                                retry_at = retry_at.replace(tzinfo=UTC)
                            delay = (retry_at - datetime.now(UTC)).total_seconds()
                        except (ValueError, TypeError, OverflowError):
                            pass
                if not math.isfinite(delay):
                    delay = 0.25 * (2**attempt)
                if delay > 2:
                    break  # Do not retry earlier than a long server rate-limit instruction.
                await asyncio.sleep(max(0, delay))
                continue
            break
        if not 200 <= response.status_code < 300:
            messages = {
                400: "Jira rejected the request; check fields, issue types, and project settings",
                401: "Jira authentication failed; check the locally configured email and token",
                403: "Jira denied access; check account and project permissions",
                404: "Jira resource was not found or is not visible to this account",
                429: "Jira rate limit reached; retry later",
            }
            public_status = response.status_code if response.status_code in messages else 502
            raise JiraError(
                messages.get(response.status_code, "Jira returned an unexpected response"),
                public_status,
            )
        if response.status_code == 204 or not response.content:
            return {}
        try:
            data = response.json()
        except ValueError:
            raise JiraError("Jira returned invalid JSON") from None
        if not isinstance(data, dict):
            raise JiraError("Jira returned an unexpected response shape")
        return data
