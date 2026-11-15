"""Official MCP SDK v2 adapter; local stdio only until enterprise auth is designed."""

import logging
from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from halo.client import JiraClient
from halo.config import Settings
from halo.errors import JiraError
from halo.models import IssueCreate, IssueUpdate, Search
from halo.service import JiraService


def create_server(settings: Settings | None = None) -> MCPServer:
    config = settings or Settings()
    server = MCPServer(
        "HALO Jira", instructions="Jira operations for authorized local clients only."
    )

    async def invoke(method: str, *args, **kwargs) -> dict:
        # A fresh short-lived client avoids global event-loop and resource-lifetime issues.
        client = JiraClient(config)
        try:
            return await getattr(JiraService(client), method)(*args, **kwargs)
        except JiraError as exc:
            raise ToolError(str(exc)) from None
        except (ValidationError, ValueError):
            raise ToolError("Invalid Jira operation inputs") from None
        finally:
            await client.close()

    @server.tool()
    async def jira_current_user() -> dict:
        """Validate Jira authentication and retrieve the current user."""
        return await invoke("current_user")

    @server.tool()
    async def jira_list_projects(start_at: int = 0, max_results: int = 50) -> dict:
        """List a page of visible projects; follow startAt/maxResults pagination."""
        return await invoke("projects", start_at, max_results)

    @server.tool()
    async def jira_get_project(project_key: str) -> dict:
        """Retrieve details of an accessible Jira project."""
        return await invoke("project", project_key)

    @server.tool()
    async def jira_create_issue(
        project_key: str,
        summary: str,
        issue_type: Literal["Task", "Story", "Bug"] = "Task",
        description: str | None = None,
    ) -> dict:
        """Create one issue. This changes Jira; never blindly retry after a timeout."""
        try:
            data = IssueCreate(
                project_key=project_key,
                summary=summary,
                issue_type=issue_type,
                description=description,
            )
        except ValidationError:
            raise ToolError("Invalid issue fields") from None
        return await invoke("create_issue", data)

    @server.tool()
    async def jira_get_issue(issue_key: str) -> dict:
        """Retrieve an issue by key."""
        return await invoke("get_issue", issue_key)

    @server.tool()
    async def jira_update_issue(
        issue_key: str, summary: str | None = None, description: str | None = None
    ) -> dict:
        """Update an issue summary or description."""
        try:
            data = IssueUpdate(summary=summary, description=description)
        except ValidationError:
            raise ToolError("Provide valid issue update fields") from None
        return await invoke("update_issue", issue_key, data)

    @server.tool()
    async def jira_get_transitions(issue_key: str) -> dict:
        """List currently allowed workflow transitions."""
        return await invoke("transitions", issue_key)

    @server.tool()
    async def jira_transition_issue(issue_key: str, transition_id: str) -> dict:
        """Perform one currently allowed workflow transition."""
        return await invoke("transition", issue_key, transition_id)

    @server.tool()
    async def jira_add_comment(issue_key: str, body: str) -> dict:
        """Add one plain-text comment encoded as Atlassian Document Format."""
        return await invoke("add_comment", issue_key, body)

    @server.tool()
    async def jira_search_issues(
        jql: str, max_results: int = 25, next_page_token: str | None = None
    ) -> dict:
        """Search using Jira enhanced JQL search and token pagination."""
        try:
            data = Search(jql=jql, max_results=max_results, next_page_token=next_page_token)
        except ValidationError:
            raise ToolError("Invalid search inputs") from None
        return await invoke("search", data)

    @server.resource("halo://architecture")
    def architecture() -> str:
        """Describe how the local server fits into HALO."""
        return (
            "HALO workflow -> REST or MCP adapter -> shared JiraService -> JiraClient -> Jira Cloud"
        )

    return server


def main() -> None:
    try:
        server = create_server()
    except (ValidationError, ValueError):
        raise SystemExit(
            "Configure Jira settings in a local .env or environment before starting MCP"
        ) from None
    logging.getLogger("httpx").setLevel(logging.WARNING)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
