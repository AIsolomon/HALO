"""Small commands for learning and operating the integration."""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from pydantic import ValidationError

from halo.client import JiraClient
from halo.config import Settings
from halo.errors import JiraError, WorkflowConflict
from halo.gateways import McpGateway, RestGateway
from halo.models import IssueCreate, IssueUpdate, Search
from halo.service import JiraService
from halo.workflow import RunStore, Workflow, WorkflowSpec


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="HALO Jira connectivity and local workflow tools")
    subs = result.add_subparsers(dest="command", required=True)
    subs.add_parser("check", help="Authenticate and retrieve current user and first project page")
    project = subs.add_parser("project", help="Retrieve project details")
    project.add_argument("key")
    get = subs.add_parser("get", help="Retrieve one issue")
    get.add_argument("key")
    create = subs.add_parser("create", help="Create exactly one test issue")
    create.add_argument("--project", required=True)
    create.add_argument("--summary", required=True)
    create.add_argument("--type", choices=["Task", "Story", "Bug"], default="Task")
    create.add_argument("--description")
    update = subs.add_parser("update", help="Update an existing issue")
    update.add_argument("key")
    update.add_argument("--summary")
    update.add_argument("--description")
    transitions = subs.add_parser("transitions", help="List currently allowed transitions")
    transitions.add_argument("key")
    move = subs.add_parser("move", help="Transition an issue to a reachable status name")
    move.add_argument("key")
    move.add_argument("--status", required=True)
    comment = subs.add_parser("comment", help="Add one plain-text comment")
    comment.add_argument("key")
    comment.add_argument("--body", required=True)
    search = subs.add_parser("search", help="Search one page of Jira issues")
    search.add_argument("jql")
    search.add_argument("--max-results", type=int, default=25)
    search.add_argument("--next-page-token")
    for sub in (create, update, move, comment):
        sub.add_argument("--allow-live-write", action="store_true")
    serve = subs.add_parser("serve", help="Run local REST service at http://127.0.0.1:8000/docs")
    serve.add_argument("--port", type=int, default=8000)
    subs.add_parser("mcp", help="Run local stdio MCP server")
    demo = subs.add_parser("demo", help="Run the end-to-end simulator, with no live Jira writes")
    demo.add_argument("--report", type=Path)
    wf = subs.add_parser("workflow", help="Start a workflow or approve a paused execution")
    wf.add_argument("--route", choices=["rest", "mcp"], required=True)
    wf.add_argument("--action", choices=["run", "approve"], default="run")
    wf.add_argument("--run-id", default=None)
    wf.add_argument("--project", default=None)
    wf.add_argument("--summary", default="HALO integration demonstration")
    wf.add_argument("--development-status", default="In Progress")
    wf.add_argument("--testing-status")
    wf.add_argument("--done-status", default="Done")
    wf.add_argument("--test-failed", action="store_true")
    wf.add_argument("--api-url", default="http://127.0.0.1:8000")
    wf.add_argument("--allow-live-write", action="store_true")
    return result


def subprocess_environment(settings: Settings) -> dict[str, str]:
    # Pass only Jira settings; never forward unrelated GitHub/cloud credentials.
    network_env = {
        key: os.environ[key]
        for key in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "no_proxy",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        )
        if key in os.environ
    }
    return {
        **network_env,
        "JIRA_BASE_URL": settings.jira_base_url,
        "JIRA_EMAIL": settings.jira_email,
        "JIRA_API_TOKEN": settings.jira_api_token.get_secret_value(),
        "JIRA_PROJECT_KEY": settings.jira_project_key,
        "HALO_DEMO": str(settings.halo_demo).lower(),
    }


async def workflow_command(args, config: Settings) -> dict:
    if args.action == "approve" and not args.run_id:
        raise ValueError("Approval requires an existing --run-id")
    if args.route == "rest":
        url = urlsplit(args.api_url)
        if url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("This local workflow client requires a loopback HTTP REST URL")
        if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise ValueError("REST URL must be a loopback origin")
        if not config.halo_api_key.get_secret_value():
            raise ValueError("Configure HALO_API_KEY locally for the REST workflow client")
    store = RunStore(config.halo_workflow_db)

    async def execute(gateway):
        workflow = Workflow(
            gateway, store, args.route, target=f"{config.jira_base_url}|{config.jira_email}"
        )
        if args.action == "approve":
            return await workflow.approve(args.run_id)
        spec = WorkflowSpec(
            run_id=args.run_id or str(uuid4()),
            project_key=args.project or config.jira_project_key,
            summary=args.summary,
            development_status=args.development_status,
            testing_status=args.testing_status,
            done_status=args.done_status,
            test_failed=args.test_failed,
        )
        return await workflow.run(spec)

    try:
        if args.route == "rest":
            async with httpx.AsyncClient(
                base_url=args.api_url,
                timeout=config.halo_timeout_seconds,
                trust_env=False,
                headers={"X-HALO-API-Key": config.halo_api_key.get_secret_value()},
            ) as http:
                return await execute(RestGateway(http))
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "halo.mcp_server"],
            env=subprocess_environment(config),
        )
        async with Client(params) as client:
            return await execute(McpGateway(client))
    finally:
        store.close()


async def run(args, config: Settings) -> dict:
    writes = {"create", "update", "move", "comment", "workflow"}
    if args.command in writes and not config.halo_demo and not args.allow_live_write:
        raise ValueError("Live writes require --allow-live-write and a dedicated Jira test project")
    if args.command == "workflow":
        return await workflow_command(args, config)
    client = JiraClient(config)
    jira = JiraService(client)
    try:
        match args.command:
            case "check":
                user = await jira.current_user()
                projects = await jira.projects()
                return {
                    "mode": "demo" if config.halo_demo else "live",
                    "user": {"displayName": user.get("displayName"), "active": user.get("active")},
                    "projects": projects,
                }
            case "project":
                return await jira.project(args.key)
            case "get":
                return await jira.get_issue(args.key)
            case "create":
                return await jira.create_issue(
                    IssueCreate(
                        project_key=args.project,
                        summary=args.summary,
                        issue_type=args.type,
                        description=args.description,
                    )
                )
            case "update":
                return await jira.update_issue(
                    args.key, IssueUpdate(summary=args.summary, description=args.description)
                )
            case "transitions":
                return await jira.transitions(args.key)
            case "move":
                return await jira.transition_to(args.key, args.status)
            case "comment":
                return await jira.add_comment(args.key, args.body)
            case "search":
                return await jira.search(
                    Search(
                        jql=args.jql,
                        max_results=args.max_results,
                        next_page_token=args.next_page_token,
                    )
                )
            case _:
                raise ValueError("Unknown command")
    finally:
        await client.close()


def main() -> None:
    args = parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        if args.command == "demo":
            from halo.demo import run_demo

            report = asyncio.run(run_demo())
            output = json.dumps(report, indent=2)
            print(output)
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(output + "\n")
            return
        config = Settings()
        if args.command == "serve":
            import uvicorn

            from halo.api import create_app

            uvicorn.run(create_app(config), host="127.0.0.1", port=args.port, access_log=False)
        elif args.command == "mcp":
            from halo.mcp_server import create_server

            create_server(config).run(transport="stdio")
        else:
            print(json.dumps(asyncio.run(run(args, config)), indent=2))
    except ValidationError:
        raise SystemExit(
            "Invalid settings or inputs. Check .env.example and command help; "
            "credentials are intentionally omitted from errors."
        ) from None
    except (JiraError, WorkflowConflict, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
