"""Workflow ports: the same business calls over REST or an MCP client."""

import json
from typing import Protocol

import httpx
from mcp import Client

from halo.errors import JiraError


class Gateway(Protocol):
    async def call(self, operation: str, data: dict) -> dict: ...


class RestGateway:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def call(self, operation: str, data: dict) -> dict:
        data = dict(data)
        key = data.pop("issue_key", "")
        routes = {
            "create_issue": ("POST", "/jira/issues"),
            "get_issue": ("GET", f"/jira/issues/{key}"),
            "update_issue": ("PUT", f"/jira/issues/{key}"),
            "get_transitions": ("GET", f"/jira/issues/{key}/transitions"),
            "transition_issue": ("POST", f"/jira/issues/{key}/transitions"),
            "add_comment": ("POST", f"/jira/issues/{key}/comments"),
        }
        method, path = routes[operation]
        try:
            response = await self.http.request(method, path, json=data if method != "GET" else None)
        except httpx.RequestError:
            raise JiraError("HALO REST service is unreachable or timed out") from None
        if response.is_error:
            raise JiraError(
                "HALO REST operation failed; inspect the server status", response.status_code
            )
        return response.json()


class McpGateway:
    def __init__(self, client: Client):
        self.client = client

    async def call(self, operation: str, data: dict) -> dict:
        result = await self.client.call_tool(f"jira_{operation}", data)
        if result.is_error:
            raise JiraError("HALO MCP operation failed; inspect the tool error locally")
        if result.structured_content is not None:
            return result.structured_content
        for content in result.content:
            if content.type == "text":
                return json.loads(content.text)
        raise JiraError("HALO MCP returned no structured result")
