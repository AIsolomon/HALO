# HALO

**Harness for Agentic Lifecycle Orchestration**

An incremental, framework-independent Jira Cloud integration project for HALO,
covering a reusable Python client, REST and MCP adapters, and workflow simulation.

## Current status

Repository initialized. Application implementation has not started.
The first development task is **Phase 1, Step 1: environment setup**.
No Jira connection or issue creation has been attempted.

## Planned architecture

```text
HALO workflow simulator
        |           |
     FastAPI     MCP server
        |           |
        Jira service
             |
        Jira HTTP client
             |
     Jira Cloud REST API v3
```

REST and MCP will share the same Jira operations. Business logic will remain
independent of LLMs and orchestration frameworks.

## Repository guide

- `docs/PROJECT_BRIEF.md`: original project requirements and teaching approach.
- `AGENTS.md`: instructions for contributors and coding assistants.
- `TASKS.md`: phased progress tracker.
- `DECISIONS.md`: architectural decisions and implementation boundaries.
- `.env.example`: configuration names with placeholder values only.
- `.gitignore`: excludes credentials, virtual environments, and generated files.

## Next development step

Inspect the target development system and verify supported Python and dependency
versions against official documentation before installing packages. The preferred
stack is Python, uv, HTTPX, and later Pydantic v2, FastAPI, the official Python MCP
SDK, pytest, and Ruff. No package versions have been selected or verified yet.

For local Jira authentication, copy `.env.example` to `.env` and edit it locally.
Never paste API tokens into chat or commit them. The template is documentation;
Python will not load `.env` automatically until configuration loading is implemented.
Use a dedicated Jira development project and least-privilege credentials.

The initial milestone is to authenticate, list Jira projects, and create one test
issue. Complete and validate each phase before moving to the next, with approval
at major phase boundaries.
