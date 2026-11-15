# Learning guide

Read this in small sections. The original request was deliberately incremental;
the later request authorized an unattended end-to-end implementation. These notes
preserve the teaching path so you can review one layer at a time before extending it.
The questions are for your next review session; no answer was assumed during the build.

## Git, Python, and the environment

A Git repository is the folder plus its hidden `.git` history. A commit is a saved
snapshot. GitHub is a remote host for another copy of that history. Local commits
already work; a GitHub push is still blocked by the connection's permissions.

Python executes the application. `uv` installs dependencies into `.venv`, preventing
this project's packages from conflicting with other projects. `pyproject.toml`
declares the project and its direct dependencies; `uv.lock` records the complete
resolved versions and download hashes. `src/halo` is a Python package: related
modules that can import each other. `__init__.py` identifies the package.

`uv run halo check` calls the function registered as the `halo` command in
`pyproject.toml`. You can also run `python -m halo.cli` using the project's Python.
An `import` makes another module's functions or classes available. A class groups
state and related behavior; `__init__` initializes an instance. `self` is that instance.

Check your understanding: why is `.venv` excluded from Git? What does GitHub add
beyond the Git repository already on disk?

## APIs using this Jira project

An HTTP API accepts a request at a URL and returns a status code plus optional data.
For example, `https://your-site.atlassian.net/rest/api/3/myself` identifies an endpoint
on your Jira site. GET retrieves information; POST creates an issue, comment, or
transition; PUT updates fields. Jira enhanced search also uses POST because the
JQL query is carried in a JSON body, even though searching does not modify issues.

JSON represents objects, arrays, strings, numbers, booleans, and null. A Python
`dict` becomes a JSON object when HTTPX receives `json=...`. A Python `list` becomes
an array. For a create request, `fields.project.key` selects your project, and
`fields.issuetype.name` selects Task, Story, or Bug.

`TEST` is a project key. `TEST-17` is one issue in that project. Status is the current
state of an issue; a transition is an action that moves it to another permitted
state. Transition IDs are not universal. The application discovers them rather
than guessing that a particular numeric ID means Done in every project.

Jira REST v3 expects rich descriptions and comments in Atlassian Document Format
(ADF), a JSON document tree. `models.adf` converts a plain string into paragraphs
inside a document. It does not accept arbitrary rich document editing yet.

For local development, HTTPX builds an HTTP Basic authentication header from email
and API token. HTTPS protects it in transit. This does not turn a personal token
into an enterprise identity scheme. Never print the authentication header.

Typical statuses: 200 means read succeeded, 201 means created, and 204 means success
without a response body. 400 means Jira rejected the fields; 401 is authentication;
403 is denied access; 404 can mean absent or invisible; 409 is a workflow conflict;
422 is invalid REST input; 429 is rate limiting. A timeout after a write is uncertain:
the issue may exist even though the response did not arrive.

Check your understanding: why do we list transitions before moving an issue? Why
is automatically retrying a timed-out issue creation risky?

## Shared service and asynchronous Python

The execution path is `CLI / REST / MCP -> JiraService -> JiraClient -> Jira`.
The service builds Jira's request bodies. The client owns HTTP configuration and
safe errors. Reusing these components means that a fix to ADF formatting applies
to REST and MCP without copying the fix into two adapters.

A type hint such as `key: str` documents the input type. `-> dict` documents the
result. Python does not enforce every type hint at runtime; Pydantic models validate
business inputs. `IssueCreate(...)` rejects an empty summary before contacting Jira.

`async def` defines an asynchronous function. `await` pauses that operation while
network I/O finishes, allowing the event loop to handle other work. It does not
mean a request is sent twice. `async with` manages asynchronous resource lifetimes;
`try/finally` ensures the HTTP client closes even if a request fails.

A constructor receives a client: `JiraService(client)`. This is dependency injection
in its simplest form. Tests inject a controlled HTTP transport instead of using a
real Jira token. No container or orchestration framework is needed.

A raised exception stops the normal path. Adapters translate `JiraError` into a safe
CLI message, HTTP error, or MCP tool error. `raise ... from None` prevents sensitive
low-level exception context from being printed as part of a user-facing failure.

Check your understanding: which layer should change if Jira renames an endpoint?
Which layer should change if we replace local configuration with a vault?

## REST and MCP

FastAPI maps HTTP methods and paths to Python functions. A decorator such as
`@app.post("/jira/issues")` registers an endpoint. FastAPI validates the annotated
input model, calls the shared service, and serializes the result. Swagger UI is an
interactive client generated from the OpenAPI schema, not a second implementation.
A dependency performs API-key authorization before the endpoint touches Jira.

MCP is a protocol between a host application and capability servers. A host owns
one or more clients; the client discovers tools and calls a server. A tool is a
named operation with an input schema. A resource exposes contextual data, such as
`halo://architecture`. The official Python SDK derives schemas from function
signatures and handles the protocol. An LLM is optional: our test client calls the
tools directly and checks their structured results.

With stdio, the host starts a process and exchanges messages over its standard
input/output. Never print ordinary messages to stdout in that server. With
Streamable HTTP, a server has a network endpoint and can serve remote clients.
Authentication and authorization are separate requirements: proving caller
identity does not automatically authorize all Jira write operations. This build
uses stdio locally; hosted MCP and enterprise OAuth remain future work.

Check your understanding: what code do REST and MCP share? Why can we test MCP
without a model or AI agent?

## Workflow execution and human approval

`WorkflowSpec` holds a run ID, project, summary, configured target statuses, and a
simulated test result. `Workflow` calls a `Gateway` protocol implemented by REST
and MCP clients. The protocol is useful here because it lets orchestration choose
a transport without embedding Jira HTTP details.

SQLite stores each execution ID and its issue/bug keys. A unique primary key
prevents the same execution from creating a second initial task. A fingerprint
rejects reuse of an execution ID with changed inputs, route, or Jira site/account.
A completed or paused execution can be read again safely. An uncertain execution
requires manual reconciliation against Jira.

The workflow pauses at `awaiting_approval`; it does not pretend that silence means
approval. `halo workflow --action approve ...` is a separate explicit operation.
Only the simulator automatically issues that operation for its fake tasks.

The tests do not constitute enterprise certification. The local service still
needs corporate identity, scoped permissions, operational policies, and production
validation before use by untrusted callers.

Check your understanding: what information is lost if the workflow database is
deleted? Why does a failed create response require checking Jira before rerunning?
