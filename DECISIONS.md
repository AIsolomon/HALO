# Decisions

## 001 — Scope of initial repository

Initialize the repository and preserve the requirements. Do not generate the
application or install unverified dependencies as part of repository creation.
Future implementation starts with Phase 1, Step 1.

## 002 — Shared Jira integration

Build the Python Jira client first. Later REST and MCP adapters will share a Jira
service. Keep workflow orchestration and LLM dependencies outside core operations.
HALO's runtime and integration contract are currently unknown.

## 003 — Credentials and environment

Store development credentials only in local environment variables or an ignored
`.env` file. Track only a placeholder template. Do not include production secrets.
Timeouts and safe errors are baseline requirements for the first HTTP client.
Centralized authentication remains a later enterprise integration decision.

## 004 — Dependencies

Prefer Python with uv and HTTPX for initial connectivity. Select and pin versions
only after checking official support and compatibility. Add other dependencies
when the relevant phase needs them.

## 005 — Source control

Use `main` as the initial branch. This setup creates a local Git repository only;
no hosted remote or visibility setting has been selected.
