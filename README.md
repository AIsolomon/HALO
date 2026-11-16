# HALO

**Harness for Agentic Lifecycle Orchestration** — a framework-independent Jira Cloud
integration with a shared Python service, FastAPI REST adapter, official MCP SDK
server, and a small workflow simulator.

**Status:** local end-to-end REST and MCP flows pass against a Jira simulator.
Real Jira is **not yet verified** because no account credentials are configured.
The target GitHub repository is `solbaviangel/HALO`. Publishing is pending because
the currently connected account cannot access it.
See [the handoff](docs/HANDOFF.md) for results and remaining steps.

For your laptop, start with [the VS Code setup guide](docs/LOCAL_VSCODE.md).

## Run the complete local demo

Requires Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/).
`uv sync` installs the versions in the committed lockfile into `.venv`.
`halo demo` starts temporary loopback HTTP servers and an MCP subprocess, runs the
workflow through both adapters, prints the results, and stops those processes.
It requires no Jira account and does not contact real Jira.

```bash
uv sync --frozen
uv run --frozen halo demo --report reports/demo.json
```

Expect both routes to report `"state": "completed"`, ten discovered MCP tools,
and `"live_jira_verified": false`. The demo explicitly approves simulated runs;
live workflow commands pause until you run a separate approval command.

## Connect your real Jira account

Read [the setup guide](docs/SETUP.md) before configuring credentials or issuing writes.
Copy `.env.example` to `.env` and edit it locally. Never paste secrets into chat.
`halo check` reads your current Jira user and the first page of visible projects.

```bash
uv run --frozen halo check
```

Start REST locally with `uv run --frozen halo serve`; open
`http://127.0.0.1:8000/docs` and use **Authorize** with your local `HALO_API_KEY`.
Start local MCP with `uv run --frozen halo mcp` from a compatible host, with this
repository as its working directory. MCP communicates over stdio; it is not a web page.

## Architecture

```text
HALO workflow (execution ID + local SQLite state)
                   |
             REST or MCP client
              /           \
      FastAPI adapter   MCP stdio adapter
              \           /
              Shared JiraService
                     |
               HTTPX JiraClient
                     |
            Jira Cloud REST API v3
```

Descriptions and comments use Atlassian Document Format. Search uses the enhanced
`/rest/api/3/search/jql` endpoint and supports page tokens. Workflow statuses are
configurable and resolved through the issue's currently allowed transitions.

## Checks

`pytest` includes unit, credential-safety, REST authorization, workflow recovery,
and real local HTTP/MCP transport tests. It creates no real Jira tickets.

```bash
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv pip check
```

## Documentation

- [Handoff and remaining work](docs/HANDOFF.md)
- [Setup, commands, expected output, and troubleshooting](docs/SETUP.md)
- [Python and API learning guide](docs/LEARNING_GUIDE.md)
- [Module-by-module explanation](docs/MODULES.md)
- [Verified environment and package versions](docs/ENVIRONMENT.md)
- [Security boundaries and recovery](docs/SECURITY.md)
- [Official Atlassian MCP alternative](docs/ROVO_EVALUATION.md)
- [Original brief](docs/PROJECT_BRIEF.md), [progress](TASKS.md), and [decisions](DECISIONS.md)

This is a tested local integration foundation. Enterprise identity, distributed
workflow guarantees, hosted MCP authentication, and production deployment require
further work. No license has been selected for the client's project.
