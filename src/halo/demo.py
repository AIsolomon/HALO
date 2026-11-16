"""Run real local HTTP and MCP connections against a simulated Jira boundary."""

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from halo.demo_jira import DEMO_API_KEY, DEMO_EMAIL, DEMO_TOKEN
from halo.gateways import McpGateway, RestGateway
from halo.workflow import RunStore, Workflow, WorkflowSpec


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_ready(url: str, process: subprocess.Popen, auth=None) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("A demo server exited; inspect the local demo log")
        try:
            if httpx.get(url, auth=auth, timeout=0.5, trust_env=False).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Timed out waiting for a local demo server")


def stop_demo_processes(processes: list[subprocess.Popen]) -> None:
    """Stop only the server trees started by this demo, then reap their launchers."""
    for process in reversed(processes):
        if process.poll() is not None:
            continue
        if sys.platform == "win32":
            # Windows venv/Conda launchers may have child interpreters. Killing only
            # the launcher leaves those children holding the inherited log handle.
            taskkill = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32/taskkill.exe"
            subprocess.run(
                [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        else:
            try:
                process.terminate()
            except ProcessLookupError:
                pass  # The server exited between the status check and shutdown.
    for process in reversed(processes):
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@contextmanager
def demo_environment(directory: Path):
    jira_port = free_port()
    api_port = free_port()
    while api_port == jira_port:
        api_port = free_port()
    jira_url = f"http://127.0.0.1:{jira_port}"
    api_url = f"http://127.0.0.1:{api_port}"
    # Keep the Windows runtime's normal user/temp paths without passing unrelated
    # credentials into the simulator processes.
    inherited = (
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "SYSTEMDRIVE",
        "TEMP",
        "TMP",
        "APPDATA",
        "LOCALAPPDATA",
        "USERPROFILE",
        "PATHEXT",
    )
    env = {key: os.environ[key] for key in inherited if key in os.environ}
    env.update(
        {
            "HALO_DEMO": "true",
            "JIRA_BASE_URL": jira_url,
            "JIRA_EMAIL": DEMO_EMAIL,
            "JIRA_API_TOKEN": DEMO_TOKEN,
            "JIRA_PROJECT_KEY": "TEST",
            "HALO_API_KEY": DEMO_API_KEY,
            "PYTHONUNBUFFERED": "1",
        }
    )
    processes = []
    log_path = directory / "servers.log"
    try:
        with log_path.open("w", encoding="utf-8") as log:
            try:
                for target, port in (
                    ("halo.demo_jira:create_app", jira_port),
                    ("halo.api:create_app", api_port),
                ):
                    processes.append(
                        subprocess.Popen(
                            [
                                sys.executable,
                                "-m",
                                "uvicorn",
                                target,
                                "--factory",
                                "--host",
                                "127.0.0.1",
                                "--port",
                                str(port),
                                "--log-level",
                                "warning",
                                "--no-access-log",
                            ],
                            env=env,
                            cwd=directory,
                            stdout=log,
                            stderr=log,
                        )
                    )
                    if len(processes) == 1:
                        wait_ready(
                            f"{jira_url}/rest/api/3/myself", processes[-1], (DEMO_EMAIL, DEMO_TOKEN)
                        )
                    else:
                        wait_ready(f"{api_url}/health", processes[-1])
                yield api_url, env
            finally:
                stop_demo_processes(processes)
    except Exception as exc:
        # Read diagnostics only after closing the parent's log handle and stopping
        # the server trees. All children use public simulator settings, never Jira secrets.
        try:
            log_text = log_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            log_text = ""  # Never mask the actual failure with a diagnostics read error.
        if log_text:
            exc.add_note(f"Local demo server log (last 8000 characters):\n{log_text[-8000:]}")
        raise


async def exercise_rest(api_url: str, store: RunStore) -> dict:
    async with httpx.AsyncClient(
        base_url=api_url, timeout=15, trust_env=False, headers={"X-HALO-API-Key": DEMO_API_KEY}
    ) as http:
        me = await http.get("/jira/me")
        me.raise_for_status()
        projects = await http.get("/jira/projects")
        projects.raise_for_status()
        project = await http.get("/jira/projects/TEST")
        project.raise_for_status()
        gateway = RestGateway(http)
        # Exercise create, update, read, transition, and comments via a complete workflow.
        workflow = Workflow(gateway, store, "rest")
        spec = WorkflowSpec(run_id="demo-rest", project_key="TEST", test_failed=True)
        paused = await workflow.run(spec)
        assert paused["state"] == "awaiting_approval"
        assert paused["bug_key"]
        replay = await workflow.run(spec)
        assert replay["issue_key"] == paused["issue_key"]
        await gateway.call(
            "update_issue", {"issue_key": paused["issue_key"], "summary": "HALO REST demo updated"}
        )
        # This explicit approval is for simulated issues only.
        completed = await workflow.approve(spec.run_id)
        issue = await gateway.call("get_issue", {"issue_key": completed["issue_key"]})
        assert issue["fields"]["status"]["name"] == "Done"
        assert issue["fields"]["summary"] == "HALO REST demo updated"
        search = await http.post("/jira/search", json={"jql": "project = TEST", "max_results": 1})
        search.raise_for_status()
        first = search.json()
        assert first["nextPageToken"]
        next_page = await http.post(
            "/jira/search",
            json={"jql": "project = TEST", "next_page_token": first["nextPageToken"]},
        )
        next_page.raise_for_status()
        assert next_page.json()["issues"]
        return {
            "state": completed["state"],
            "issue_key": completed["issue_key"],
            "bug_key": completed["bug_key"],
            "duplicate_prevention": "passed",
            "search_pagination": "passed",
            "approval_gate": "passed",
        }


async def exercise_mcp(env: dict, store: RunStore) -> dict:
    params = StdioServerParameters(command=sys.executable, args=["-m", "halo.mcp_server"], env=env)
    async with Client(params) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert len(names) == 10
        gateway = McpGateway(client)
        result = await client.call_tool("jira_current_user", {})
        assert not result.is_error
        projects = await client.call_tool("jira_list_projects", {})
        assert not projects.is_error
        project = await client.call_tool("jira_get_project", {"project_key": "TEST"})
        assert not project.is_error
        workflow = Workflow(gateway, store, "mcp")
        spec = WorkflowSpec(run_id="demo-mcp", project_key="TEST")
        paused = await workflow.run(spec)
        assert paused["state"] == "awaiting_approval"
        await gateway.call(
            "update_issue",
            {"issue_key": paused["issue_key"], "description": "Updated through the MCP transport"},
        )
        completed = await workflow.approve(spec.run_id)
        issue = await gateway.call("get_issue", {"issue_key": completed["issue_key"]})
        assert issue["fields"]["status"]["name"] == "Done"
        search = await client.call_tool("jira_search_issues", {"jql": "project = TEST"})
        assert not search.is_error
        bad = await client.call_tool("jira_get_issue", {"issue_key": "../invalid"})
        assert bad.is_error
        return {
            "state": completed["state"],
            "issue_key": completed["issue_key"],
            "discovered_tools": sorted(names),
            "invalid_input_rejected": True,
            "approval_gate": "passed",
        }


async def run_demo() -> dict:
    with tempfile.TemporaryDirectory(prefix="halo-demo-") as temp:
        directory = Path(temp)
        with demo_environment(directory) as (api_url, env):
            store = RunStore(str(directory / "runs.sqlite3"))
            try:
                return {
                    "mode": "local_simulator",
                    "live_jira_verified": False,
                    "rest": await exercise_rest(api_url, store),
                    "mcp": await exercise_mcp(env, store),
                }
            finally:
                store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Optional JSON result file (no credentials)")
    args = parser.parse_args()
    report = asyncio.run(run_demo())
    text = json.dumps(report, indent=2)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n")


if __name__ == "__main__":
    main()
