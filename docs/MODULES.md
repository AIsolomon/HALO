# Module-by-module walkthrough

Run commands from the repository root using the locked environment. Real Jira
commands require the private `.env` from `SETUP.md`. Commands marked as tests or
simulator work without live credentials. A Python module is one `.py` file; the
names below correspond directly to `src/halo/`.

## `config.py` — configuration

Purpose: validate settings before any network request. Imported by CLI and server
factories. `BaseSettings` reads environment variables and `.env`; `SecretStr` masks
secrets in representations. `Field` sets bounds on the timeout. `urlsplit` separates
scheme, host, credentials, and path so the model validator can enforce a site origin.
`Settings()` returns a validated object or raises `ValidationError`. Environment
variables override the file. In HALO, replace configuration sourcing with central
secret management without moving credentials into workflow payloads.

Run `uv run halo check` after configuration. An invalid setup exits with a safe
message, and a valid one attempts read-only Jira authentication. Inspect `.env`
locally if it fails. Check: why use `SecretStr`? Why reject a URL containing credentials?

## `models.py` — business input models

Purpose: define valid operation inputs independently of either adapter. Pydantic's
`BaseModel` owns validation; `Annotated` and `StringConstraints` attach key/length
rules to type hints. `Literal` limits supported issue types. `model_validator`
rejects an update with no changes. `adf(text)` turns newline-separated text into
Jira v3's document structure. `None` means an optional field was not supplied;
clearing fields and arbitrary rich text are not currently implemented.

CLI, FastAPI, MCP, and tests construct models, which return validated objects or
raise validation errors. In HALO, the same operation contract can serve multiple
transports. Run `uv run pytest -q tests/test_client_service.py`; invalid inputs
must be rejected before any write. Check: why validate before calling Jira? Which
function converts a comment into the format Jira REST v3 expects?

## `errors.py` — shared failure types

`JiraError` subclasses `Exception`, carrying a safe message and HTTP status.
`WorkflowConflict` signals that automatic continuation is unsafe. `super()` calls
the parent exception constructor. Clients raise these; adapters translate them.
Run `uv run pytest -q tests/test_client_service.py tests/test_workflow.py` to verify
sanitization and blocked replay. In HALO these are candidates for centralized error
classification, without exposing low-level secrets. Check: why avoid raw Jira
response bodies in ordinary errors?

## `client.py` — Jira HTTP boundary

`JiraClient.__init__` imports HTTPX and creates one authenticated `AsyncClient` with
JSON headers, timeout, and redirects disabled. Live requests preserve configured
proxy/CA settings; simulator requests stay local. `request(method, path, **kwargs)`
accepts a fixed v3 path and request options, awaits HTTPX, and returns a JSON dict.
GET responses can be retried on bounded transient statuses; writes get one attempt.
`close` releases connections. Raw failures are translated to `JiraError`.

The service calls this module. `httpx.MockTransport` is the test injection point.
Run `uv run pytest -q tests/test_client_service.py`; expect all client checks to pass.
Use `halo check` for real connectivity. In enterprise HALO this client should run
centrally, with a replaceable auth strategy. Check: who closes the HTTP connection?
Why don't we retry a POST after an unknown outcome?

## `service.py` — shared Jira operations

`JiraService(client)` receives the HTTP boundary. Methods such as `create_issue`
accept a validated model, build the Jira `fields` object, call the client, and
return a response dict. `model_dump(exclude_none=True)` serializes only supplied
update values. `TypeAdapter` validates individual keys outside a full model.
`transition` confirms the requested action is available; `transition_to` resolves
a status name to a unique allowed action. Search uses enhanced JQL token pagination.

All adapters call this service. Run `halo check`, then follow the one-issue steps
in `SETUP.md`. Expected output is Jira JSON or a safe actionable error. Project
configuration can require fields this first implementation does not yet expose.
HALO's workflow framework can change without changing this class. Check: why does
request-building live here rather than in each REST endpoint?

## `api.py` — FastAPI adapter

`create_app` receives settings and optionally a test service. A nested lifespan
context closes the owned client at shutdown. Endpoint decorators register methods
and paths. `Depends`/`Security` run constant-time HALO-key authorization before
business operations. Annotated models become OpenAPI request schemas. The exception
handler maps safe Jira failures to JSON status responses. Middleware emits a
correlation ID and structured route-level log without content or credentials.

Run `uv run halo serve`, open `/docs`, authorize with the HALO key, and try GET
`/jira/me`. Test with `uv run pytest -q tests/test_api.py`. An unauthenticated call
must return 401 without contacting Jira. Enterprise HALO needs corporate identity
and operation-level policy instead of this local shared key. Check: what does
`/health` prove? Why is the HALO key different from the Jira token?

## `mcp_server.py` — official SDK adapter

`create_server` registers ten tools and one architecture resource using official
`MCPServer` decorators. Tool parameters define discovery schemas. `invoke` creates
a short-lived Jira client, calls the same service method used by REST, translates
failures to `ToolError`, and always closes the client in `finally`. Model creation
errors are sanitized before the SDK reports them. No LLM is imported.

The entry point runs stdio only. Run `uv run halo demo` to watch discovery and
execution, or configure `uv run halo mcp` in a local MCP host. A process waiting for
input is normal. See `exercise_mcp` for direct SDK calls. In enterprise HALO a
centrally hosted authenticated transport can wrap these business operations after
security design. Check: what belongs on stderr rather than stdout? Who launches
a stdio server process?

## `gateways.py` — transport clients for orchestration

`Gateway` is a Python `Protocol`: a useful small interface because two transports
implement the same `call(operation, data)` operation. `RestGateway` maps operation
names to REST methods/paths using an HTTPX client. `McpGateway` calls tool names and
extracts structured results using the official MCP client. Neither builds Jira
REST payloads. Both return dicts or safe errors.

`Workflow` calls these clients; the demo supplies actual local servers. Run
`uv run pytest -q tests/test_e2e.py` to verify both. In HALO these are examples of
workflow capability clients. Check: which gateway would a REST-only engine use?

## `workflow.py` — simulator and durable local state

`WorkflowSpec` validates IDs and configurable stages. `RunStore` uses Python's
standard `sqlite3`; parameterized SQL separates values from commands. A primary-key
claim records a run before network I/O. `hashlib` fingerprints its target/inputs.
`Workflow.run` creates a task, changes status, simulates testing, optionally creates
a bug, and pauses for human approval. It saves issue keys immediately. `approve`
claims a paused execution before transitioning to its configured final status.

The CLI chooses a gateway; the workflow returns its state and Jira keys. Failure
marks the run `needs_review`. Run `uv run pytest -q tests/test_workflow.py`; test
restart persistence and a successful create followed by a simulated lost response.
A full live command is documented in `SETUP.md`; it requires explicit write opt-in.
This is a teaching simulator, not HALO's final orchestration engine. Check: why
claim before calling Jira? What prevents approval against another Jira site?

## `cli.py` — commands and composition

`argparse` parses flags into a namespace. `parser` describes commands; `main`
loads settings and chooses a server or asynchronous action. `asyncio.run` starts
an event loop for CLI operations. `match` selects the command. `run` enforces live
write opt-in and owns the client lifetime. `workflow_command` composes gateway,
store, and workflow; MCP child environment forwarding is deliberately limited.

Run `uv run halo --help`, then `uv run halo demo`. Invalid inputs exit with a safe
message and nonzero status. In HALO, these commands are operator/testing entry
points rather than the orchestration framework. Check: why use a separate flag
for live writes? Which command works without any `.env`?

## `demo_jira.py` and `demo.py` — reproducible validation

`demo_jira.create_app` is a deliberately limited in-memory HTTP simulator, guarded
by `HALO_DEMO`. It implements only the subset exercised here, including project
`TEST`, basic transitions, and one basic JQL query. It does not model every Jira
permission, required field, workflow, or search behavior.

`demo_environment` starts loopback subprocesses using public fake credentials.
`wait_ready` checks process health with a deadline. `run_demo` owns a temporary
directory and SQLite store. `exercise_rest` uses actual HTTP; `exercise_mcp` uses
an actual stdio child and the official SDK. Context managers stop processes and
remove temporary state even on failure. Assertions check results, not merely the
absence of exceptions. No real issue is created.

Run `uv run halo demo --report reports/demo.json`. Expect both completed routes
and ten tools, while live Jira verification stays false. The demo cannot establish
enterprise readiness or real-account compatibility. In HALO it provides a fast
contract test environment while live credentials are unavailable. Check: which
parts of this demo are real transports? Which external system is simulated?

## Other tracked files

- `tests/`: behavior and safety checks; `conftest.py` injects fake configuration.
- `pyproject.toml`: package metadata, entry points, dependency pins, and tool options.
- `uv.lock`: complete resolution with hashes and a 16 November 2026 release cutoff.
- `.env.example`: names and placeholders only; actual `.env` is private.
- `.gitignore`: credentials, virtual environments, caches, reports, local SQLite state.
- `Dockerfile` / `.dockerignore`: non-root REST packaging and build-context exclusions.
- `.github/workflows/ci.yml`: tests/lint/dependency checks for a future GitHub remote.
- `AGENTS.md`: contributor instructions; `TASKS.md`: truthful progress.
- `DECISIONS.md`: implementation choices; `docs/PROJECT_BRIEF.md`: original requirements.
- `docs/`: setup, explanation, environment evidence, security, and handoff.
