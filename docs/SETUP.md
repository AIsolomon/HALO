# Setup and operation

## 1. Install the locked environment

Use Python 3.12 (tested) or 3.13 (permitted, not tested here), Git, and uv. The
inspected machine is a Codex Cloud Linux workspace, not your laptop. On another
machine, download or clone this repository first and open a terminal in its folder.

`cd` selects the repository folder. `uv sync --frozen` creates `.venv` and installs
exactly the locked dependencies without recalculating versions.

```bash
cd /workspace/HALO
uv sync --frozen
```

On a laptop, replace `/workspace/HALO` with the downloaded folder. In this cloud
workspace the default uv cache is read-only. Prefix uv commands with
`UV_CACHE_DIR=/workspace/work/uv-cache` if that error occurs. You do not need to
activate the virtual environment: `uv run` selects it automatically.

## 2. Run without real credentials

This command launches temporary Jira-simulator and REST processes, then launches
MCP over stdio. It creates three **simulated** issues total: a REST task, a REST bug,
and an MCP task. It checks the approval gate before explicitly approving the demo.
All simulator state is temporary. The optional JSON report is saved under `reports/`.

```bash
uv run --frozen halo demo --report reports/demo.json
```

Success: `rest.state` and `mcp.state` are `completed`, `discovered_tools` contains ten
names, and `live_jira_verified` remains `false`. An expected invalid-input MCP test
may print a tool-error message to stderr; the demo still succeeds if its JSON is printed.

## 3. Configure real Jira safely

Use a dedicated Jira Cloud development project. Confirm that Task, Story, or Bug is
available for it. For this prototype use an email address plus a personal API token
without scopes for your Jira site. Follow the official
[Atlassian authentication guide](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/).
Account policy may restrict token creation; token expiry must also be managed.
Scoped tokens using `api.atlassian.com/ex/jira/...` are not supported by this site's
current URL validator; do not work around it by changing the URL blindly.

The copy command creates a private local configuration from the tracked template.
The permission command restricts access on Linux/macOS. On Windows use
`Copy-Item .env.example .env` and your normal user file permissions instead.

```bash
cp .env.example .env
chmod 600 .env
```

Edit `.env` locally with your Jira URL, email, token, and test project key. Set
`HALO_DEMO=false`. Generate the REST API key locally, then put it in `HALO_API_KEY`.
This command prints a new random local HALO key; it is not your Jira token.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Verify that `.env` is ignored before committing. The first command should print
`.env`; the second should print nothing.

```bash
git check-ignore .env
git ls-files .env
```

`pydantic-settings` loads `.env` from the current directory. Explicit process
environment variables override the file. Never paste tokens into chat or screenshots.

## 4. First live milestone: authenticate, list projects, create one task

`check` sends GET requests to `/myself` and `/project/search`. It writes nothing.
Expect your display name and a `projects.values` list. The list can be empty if
your account lacks project access. Follow `startAt`/`maxResults` for more pages
through REST or MCP if needed.

```bash
uv run --frozen halo check
```

`project` verifies visibility of your dedicated project. Replace `TEST` with its key.

```bash
uv run --frozen halo project TEST
```

`create` issues one POST with a JSON body. `--allow-live-write` makes your intention
explicit. Do this only after the two read-only checks succeed. Expect a real issue
key such as `TEST-17`; open that issue in your Jira browser to confirm it exists.
Do not retry automatically if the connection fails after sending a create request.

```bash
uv run --frozen halo create --project TEST --summary "HALO first connectivity test" --allow-live-write
```

## 5. Validate the rest of the core client

Replace `TEST-17` with the actual key returned. `get` retrieves the issue; `update`
changes the summary. `transitions` lists actions currently allowed by your Jira
workflow. `move` finds a unique allowed transition whose target matches the given
status. Your project may use different status names or require additional fields.

```bash
uv run --frozen halo get TEST-17
uv run --frozen halo update TEST-17 --summary "HALO connectivity verified" --allow-live-write
uv run --frozen halo transitions TEST-17
uv run --frozen halo move TEST-17 --status "In Progress" --allow-live-write
uv run --frozen halo comment TEST-17 --body "Verified through the Python client" --allow-live-write
uv run --frozen halo search "project = TEST" --max-results 10
```

Search returns one page. Supply the returned `nextPageToken` using
`--next-page-token` when present. The simulator only understands `project = TEST`;
real Jira evaluates the full JQL query according to your permissions.

## 6. REST and Swagger UI

`serve` binds to loopback on port 8000. Keep this terminal open. In your browser open
`http://127.0.0.1:8000/docs`, choose **Authorize**, and enter the HALO API key stored
in `.env`. That key protects local REST calls; it is distinct from Jira authentication.
Never enter your Jira API token into Swagger's authorization box.

If the server runs in this cloud workspace, use the cloud desktop browser or a
platform-provided port preview. Your laptop's `127.0.0.1` refers to your laptop, not
the cloud server. The same localhost URL works directly when you run HALO on the laptop.

```bash
uv run --frozen halo serve
```

GET `/health` checks only the process. GET `/jira/me` checks Jira authentication.
Create, retrieve, update, transitions, comments, project details, and JQL endpoints
are listed in Swagger. A successful health check does not prove Jira connectivity.

## 7. MCP without an LLM

The command below is for an MCP host to launch as a subprocess. It exchanges JSON
protocol messages on stdin/stdout. It is expected to wait silently for a client.
Use the repository's working directory or explicit environment variables in your
host configuration; do not put a Jira token into a committed MCP config file.

```bash
uv run --frozen halo mcp
```

The automated demo and `tests/test_e2e.py` use the official SDK's `Client` and
`StdioServerParameters` to discover and call tools. Inspect `exercise_mcp` in
`src/halo/demo.py` for an executable example. `halo://architecture` is a read-only
MCP resource. Streamable HTTP hosting is intentionally deferred until its OAuth,
audience validation, TLS, and enterprise authorization design is approved.

## 8. Workflow through either adapter

A run creates one task, moves it to development, records a testing outcome, adds a
comment, then stops at `awaiting_approval`. Testing is a simulated event, not an
actual test runner. `--test-failed` additionally creates one bug; human approval can
waive that failure. No bug is resolved automatically.

For REST, first start `halo serve`. For MCP, the workflow command launches its own
stdio MCP process. Use a new run ID for each intended execution, but reuse the same
ID when checking an existing execution. Replay requires identical inputs.

```bash
uv run --frozen halo workflow --route rest --run-id learning-rest-1 --project TEST --allow-live-write
uv run --frozen halo workflow --route mcp --run-id learning-mcp-1 --project TEST --allow-live-write
```

Both routes may write to Jira. Configure `--development-status`, `--testing-status`,
and `--done-status` to match your project. Omit `--testing-status` if testing has no
separate Jira state. Results and Jira keys are retained in `work/workflows.sqlite3`.

Review the task and any bug in Jira. To explicitly approve an awaiting run, use the
same route, Jira site/account, and database. This command may transition its task to Done.

```bash
uv run --frozen halo workflow --route rest --action approve --run-id learning-rest-1 --allow-live-write
```

A `needs_review` or interrupted `running` execution is deliberately blocked from
automatic replay. See `SECURITY.md` before manually recovering uncertain operations.

## 9. Tests and container

The following checks do not touch live Jira, even if `.env` exists. Tests inject
settings, and the demo explicitly overrides them with loopback simulator settings.

```bash
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv pip check
```

Build the REST container and publish its port only on host loopback. `--env-file`
passes your private settings at runtime; `.dockerignore` excludes them from the image.
The image runs as a non-root user. Never commit `.env` or bake it into the image.

```bash
docker build -t halo-jira:local .
docker run --rm --env-file .env -p 127.0.0.1:8000:8000 halo-jira:local
```

## Common errors

| Symptom | Meaning and next action |
| --- | --- |
| Invalid settings | Check local `.env`, Jira site origin, and credentials; errors intentionally omit values. |
| 401 from Jira | Verify email/token, expiry, and account policy locally. |
| 401 from HALO | Send the HALO key in `X-HALO-API-Key`; never substitute your Jira token. |
| 403 / 404 from Jira | Check account permissions and project/issue visibility. |
| 400 on create | Check issue type, required/custom fields, and project configuration. |
| 409 on transition | List transitions; use an allowed target. Required transition fields are not implemented. |
| 422 from REST | Correct the request input shown by Swagger. |
| 429 | Respect Jira's rate limit. Long delays are surfaced instead of blocking indefinitely. |
| Timeout on a write | Inspect Jira before retrying; the write may already have succeeded. |
| Empty project page | Check site/account and browse-project permissions; use pagination. |
| Port in use | Stop the previous server or use `halo serve --port 8001`. |
| uv cache read-only in cloud | Use `UV_CACHE_DIR=/workspace/work/uv-cache` as a command prefix. |

## 10. Source control and laptop checkout

The user created `https://github.com/AIsolomon/HALO` as a public repository and
explicitly requested publishing the source there. It replaces the earlier
inaccessible `solbaviangel/HALO` destination. `origin` points to `AIsolomon/HALO`.

The repository is readable, but initial Git push and GitHub connector writes both
returned 403. Public visibility grants read access; it does not grant the connected
app write access. In GitHub Settings -> Applications -> Installed GitHub Apps,
configure the ChatGPT/Codex GitHub app and include HALO in its selected repositories.
If needed, refresh the GitHub connection in ChatGPT/Codex after that change.
Once access is available, retry the initial upload with `git push -u origin main`.

For a laptop checkout, follow `docs/LOCAL_VSCODE.md`. After committing future local
changes, this command pushes your existing `main` branch to its configured remote:

```bash
git push origin main
```

If GitHub rejects a push because the remote has new work, fetch and reconcile it
before a normal push. Do not force-push over other work. Keep `.env`, local workflow
state, virtual environments, and generated reports out of Git.
