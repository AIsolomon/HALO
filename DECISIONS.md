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

## 006 — Updated implementation authorization

The user subsequently requested an unattended end-to-end build while away. This
supersedes the initial instruction to stop after environment setup for this build.
Progress across local implementation phases is authorized; missing real credentials
still prevent claiming the original live acceptance milestones. Teaching material
is recorded for review instead of blocking the unattended work with comprehension questions.

## 007 — Tested versions and SDK API

Use verified stable releases with Python 3.12 and uv 0.13.6. Pin direct dependencies
and commit `uv.lock`, with a package upload cutoff through 16 November 2026 UTC.
Official MCP SDK 2.3.0 uses `MCPServer` and `Client`; do not copy older FastMCP v1
examples into this v2 implementation. `docs/ENVIRONMENT.md` records sources and versions.

## 008 — Honest end-to-end scope

No Jira credentials were configured. A deliberately small HTTP Jira simulator
supports contract checks over actual REST and MCP subprocess connections. Demo
reports explicitly set `live_jira_verified=false`. It is not a replacement for
real-account validation or enterprise review. No real Jira write was attempted.

## 009 — Local transport security

REST binds to loopback with an independent HALO API key. MCP uses trusted local
stdio; hosted Streamable HTTP waits for enterprise identity design. Jira remains
behind the shared service. API health does not assert Jira connectivity.

## 010 — Workflow write uncertainty

Keep execution claims and state in local SQLite, binding run IDs to inputs, route,
and Jira site/account. Record keys after writes; do not retry writes automatically.
After uncertain failures, block replay and require reconciliation rather than
pretending to provide exactly-once remote operations. Explicit human approval is
a separate action; only simulated demo tasks are auto-approved by the demo harness.

## 011 — GitHub permission boundary

The connected GitHub account is AIsolomon. An attempt to create private HALO failed
with `Resource not accessible by integration (createRepository)`. Keep local
history and document the authorized creation/push command. Do not publish client
code publicly or place it into an unrelated existing repository as a workaround.

## 012 — Container trust in this cloud

The normal Dockerfile uses public Python and locked project dependencies. This
cloud's HTTPS interception requires a certificate bundle during builds. Verification
used a temporary Dockerfile and BuildKit secret mounts for pip/uv; TLS verification
was not disabled and the environment's CA was not copied into the image. The
container runs as UID 10001. Production trust and identity remain deployment concerns.


## 013 — User-provided GitHub destination and local setup

The user supplied `https://github.com/solbaviangel/HALO` and authorized transferring
the source there. Use that exact destination, preserving any existing remote
history and visibility. The connected `AIsolomon` account receives 404 from the
GitHub connector, CLI API, and Git transport. Add the requested origin locally;
publication remains pending account/app access. Prepare a VS Code guide so the
user can clone, run the credential-free simulator, and test before configuring Jira.


## 014 — Authorized public destination

The user created `https://github.com/AIsolomon/HALO`, made it public, and explicitly
requested publishing the code there. This replaces the earlier `solbaviangel/HALO`
destination and supersedes the earlier preference for a private repository. The
connected account has push permission and the remote was empty when inspected.
Publish the existing history to `main` with a normal push, update laptop clone
instructions, and verify the resulting remote commit. Keep live Jira validation
separate from local test results.
