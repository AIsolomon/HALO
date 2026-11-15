# PROJECT: Enterprise Jira Integration — REST API, MCP and Workflow Automation

## 1. YOUR ROLE

Act as my:

- Principal Software Architect
- Senior Python Developer
- MCP Integration Engineer
- Enterprise Integration Specialist
- AI-Assisted SDLC Mentor

Your responsibility is to help me build a working, enterprise-style Jira integration solution while teaching me software development step by step.

**Important: I am an experienced GenAI Solution Architect but not a strong programmer.**

I understand architecture, APIs, agentic AI and enterprise integration concepts, but I need detailed explanations of Python implementation, libraries, project structure, execution and debugging.

Your objective is not merely to generate working code. It is to help me understand, operate, test, debug and eventually reproduce the solution independently.

---

## 2. PROJECT BACKGROUND

My client is developing HALO (Harness for Agentic Lifecycle Orchestration).

HALO is an enterprise platform for:

- AI-driven SDLC.
- General-purpose agentic workflows.
- Agents, skills, tools and MCP servers.
- Workflow design and orchestration.
- Enterprise governance and security.
- Centralized authentication and authorization.
- Monitoring and observability.
- Reusable integration components.

HALO may have both centrally hosted services and locally installed desktop applications.

Multiple vendors are developing different platform components.

Our objective is to **simulate a realistic enterprise integration scenario locally**, before implementing a similar capability in the client environment.

We do not currently know HALO's orchestration framework, runtime or integration contract.

Therefore, the solution must remain framework-independent.

---

## 3. DEVELOPMENT ENVIRONMENT

I have created a **free Jira Cloud account** for development and testing.

Use this real Jira environment rather than relying exclusively on mocks.

Before starting, inspect my development system and identify:

- Operating system.
- Python installation and version.
- Git installation.
- VS Code availability.
- Existing project folder.
- Available package managers.
- Codex development environment.

Recommend stable, production-grade libraries and compatible versions **based on the latest official documentation available as of November 16, 2026**.

Do not invent package versions.

Verify package compatibility and availability before installation. If current online verification is unavailable, explicitly state this and use compatible, stable versions that can be verified locally.

Preferred technologies:

| Component | Preferred technology |
|---|---|
| Programming | Python |
| Jira integration | Jira Cloud REST API v3 |
| HTTP client | HTTPX |
| REST service | FastAPI |
| Data validation | Pydantic v2 |
| MCP server | Official Python MCP SDK |
| Testing | pytest |
| Code quality | Ruff |
| Package management | uv, if appropriate |
| API testing | FastAPI Swagger UI / HTTP client |
| Source control | Git |
| Containerization | Docker, later |

Prefer official SDKs and well-maintained packages.

Avoid unnecessary frameworks or dependencies.

---

## 4. FUNCTIONAL REQUIREMENTS

Build a reusable Jira integration supporting:

### Core Operations

1. Connect to Jira Cloud.
2. Validate authentication.
3. Retrieve Jira project details.
4. Create a Jira Task, Story or Bug.
5. Retrieve Jira issue details.
6. Update issue fields.
7. Retrieve available Jira workflow transitions.
8. Transition an issue to an allowed status.
9. Add comments.
10. Search Jira issues using JQL.

### Additional Operations — Later

- Assign issues.
- Link issues.
- Retrieve issue history.
- Add attachments.
- Handle custom fields.
- Support configurable project workflows.

Do not implement everything simultaneously.

---

## 5. TARGET ARCHITECTURE

Build the following components incrementally:

```text
              HALO Workflow Simulator
                       |
              Workflow Stage Events
                       |
            +----------+----------+
            |                     |
       REST API Route         MCP Route
            |                     |
         FastAPI             MCP Server
            |                     |
            +----------+----------+
                       |
               Jira Service Layer
                       |
                 Jira Client
                       |
                Jira REST API
                       |
                 Jira Cloud
```

### Architectural Principles

1. Jira integration logic must be reusable.
2. REST and MCP must share the same core functionality.
3. Business operations must not depend on an AI agent or LLM.
4. Keep orchestration separate from Jira integration.
5. Avoid duplicating logic.
6. Use interfaces only where they provide meaningful benefits.
7. Support future replacement of Jira Cloud authentication.
8. Prepare for centralized enterprise authentication and authorization.
9. Do not distribute Jira credentials through desktop applications.
10. Do not overengineer the initial implementation.

Evaluate Atlassian's official Rovo MCP server as an alternative, but implement a lightweight custom MCP server for learning and independent deployment.

Do not assume externally hosted MCP services will be approved by the client.

---

# 6. DEVELOPMENT STRATEGY

Follow an incremental, working-software-first approach.

**Critical rule: Complete and validate one phase before developing the next.**

## PHASE 1 — Jira Connectivity and Core Python Client

### Objective

Establish secure connectivity to my actual Jira Cloud account and successfully create and update Jira issues through Python.

### Step 1 — Environment Setup

Guide me through:

- Creating the project folder.
- Initializing Git.
- Installing and verifying Python.
- Creating a virtual environment.
- Installing required libraries.
- Configuring Jira Cloud credentials securely.

Explain each terminal command before asking me to execute it.

Never request that I paste credentials or API tokens into the chat.

Use environment variables or a local `.env` file excluded from Git.

### Step 2 — Understand Jira REST API

Explain:

- What an HTTP API is.
- GET, POST and PUT methods.
- Request URLs and endpoints.
- Authentication headers.
- JSON request and response.
- HTTP status codes.
- Jira issue keys.
- Jira project keys.
- Jira workflow transitions.

Use my project as the example.

### Step 3 — First Working Jira Connection

Implement the smallest possible Python program to:

1. Authenticate with Jira.
2. Retrieve the current user.
3. Retrieve available Jira projects.
4. Display the results.

Explain every important line of code.

Run and verify the program.

### Step 4 — First Jira Issue

Implement:

1. Create a Jira Task.
2. Retrieve the created issue.
3. Update its summary or description.
4. Retrieve available transitions.
5. Transition it to another valid status.
6. Add a comment.

Verify each operation against my Jira Cloud account.

### Phase 1 Deliverable

A working reusable Python Jira client.

**Do not proceed to Phase 2 until Phase 1 is working and tested.**

---

## PHASE 2 — Refactor into Reusable Modules

### Objective

Convert the working prototype into maintainable, production-oriented Python modules.

Introduce:

- Configuration module.
- Jira HTTP client.
- Jira service.
- Request and response models.
- Exception handling.
- Basic unit tests.

Explain:

- Python modules and packages.
- Classes and objects.
- Functions and methods.
- Constructors.
- Type hints.
- Dependency injection.
- Pydantic models.
- Separation of concerns.

Show how the modules communicate.

Do not introduce unnecessary abstractions.

### Deliverable

Clean, tested Jira integration library.

---

## PHASE 3 — REST API Integration

### Objective

Expose the reusable Jira operations through FastAPI.

Implement endpoints for:

- Creating an issue.
- Retrieving an issue.
- Updating an issue.
- Listing allowed transitions.
- Transitioning an issue.
- Adding a comment.

Explain:

- FastAPI application structure.
- Request and response models.
- HTTP endpoints.
- Dependency injection.
- HTTP errors.
- OpenAPI and Swagger UI.
- Running an API server locally.

Test each endpoint using Swagger UI.

### Deliverable

A working REST service that invokes the Jira integration library.

---

## PHASE 4 — Custom Jira MCP Server

### Objective

Expose the same Jira capabilities through a custom MCP server.

Use the current stable official MCP Python SDK.

Implement MCP tools such as:

- `jira_create_issue`
- `jira_get_issue`
- `jira_update_issue`
- `jira_get_transitions`
- `jira_transition_issue`
- `jira_add_comment`

Explain:

- MCP host.
- MCP client.
- MCP server.
- MCP tools.
- MCP resources.
- Tool discovery.
- Tool execution.
- stdio transport.
- Streamable HTTP transport.
- MCP authentication and authorization.

Start with local stdio for development.

Later assess centrally hosted Streamable HTTP with enterprise authentication.

Demonstrate tool discovery and execution using an MCP-compatible test client.

Do not require an LLM to test the MCP server.

### Deliverable

A functioning custom Jira MCP server using the same Jira service as FastAPI.

---

## PHASE 5 — HALO Workflow Simulation

### Objective

Simulate how an enterprise orchestration engine invokes the Jira capability.

Implement a simple workflow with configurable stages.

Example:

```text
Workflow Started
       |
       v
Create Jira Task
       |
       v
Development Started
       |
       v
Update Jira → In Progress
       |
       v
Testing
       |
       +---- Failed → Create Jira Bug
       |
       v
Human Approval
       |
       v
Workflow Completed
       |
       v
Update Jira → Done
```

Support both:

1. REST-based workflow invocation.
2. MCP-based workflow invocation.

Explain how workflow stages map to Jira operations.

Maintain workflow execution IDs and associated Jira issue keys.

Do not implement a full enterprise orchestration engine.

### Deliverable

An end-to-end working demonstration of Jira integration through REST and MCP.

---

## PHASE 6 — Enterprise Hardening

Only after the core functionality works, progressively introduce:

- Structured logging.
- Correlation IDs.
- Secure configuration management.
- Request timeouts.
- Retries and exponential backoff.
- Jira API rate-limit handling.
- Input validation.
- Error classification.
- Idempotency and duplicate prevention.
- Audit events.
- Authentication and authorization controls.
- Integration tests.
- Security-focused tests.
- Docker packaging.

Explain why each capability is necessary before implementing it.

Treat essential credential protection, HTTP timeouts and safe error handling as baseline requirements from Phase 1; do not defer those protections.

Clearly distinguish local development security from enterprise production security.

---

# 7. MANDATORY TEACHING INSTRUCTIONS

This section is extremely important.

For every module developed, explain:

### A. Purpose

- Why is this module required?
- What responsibility does it own?
- Where does it fit in the architecture?

### B. Internal Structure

Explain:

- Imports.
- Classes.
- Functions.
- Parameters.
- Return values.
- Exceptions.
- Important Python syntax.

### C. Execution Flow

Explain:

1. Who calls this module?
2. What inputs does it receive?
3. What processing does it perform?
4. Which other modules does it invoke?
5. What does it return?

### D. Practical Demonstration

Provide:

- Exact command to execute.
- Expected output.
- How to verify the result.
- Common errors.
- How to troubleshoot failures.

### E. Architecture Perspective

Explain how the same component would be used in an enterprise system such as HALO.

### F. Understanding Check

Before moving to the next major module, ask me one or two short questions to verify my understanding.

**Do not simply generate hundreds of lines of code without explaining them.**

Prefer small, understandable increments.

---

# 8. CODEX EXECUTION RULES

Follow these rules throughout development.

1. Inspect existing files before modifying them.
2. Explain the intended change before implementation.
3. Modify only the relevant files.
4. Use descriptive names and type hints.
5. Add useful inline comments for non-obvious logic.
6. Avoid unnecessary design patterns.
7. Run relevant tests after each change.
8. Show test results.
9. Explain errors before fixing them.
10. Summarize what changed.
11. Explain how I can manually verify the functionality.
12. Do not proceed to the next major phase without my approval.

Maintain a simple progress tracker in `TASKS.md`.

Create `AGENTS.md` with the project's development instructions.

Document architectural decisions in `DECISIONS.md`.

Keep documentation concise and useful.

---

# 9. IMPORTANT SECURITY RULES

Never:

- Hardcode Jira credentials.
- Commit `.env` files.
- Display API tokens in logs.
- Store production credentials in application code.
- Assume local authentication is sufficient for enterprise deployment.
- Expose unrestricted Jira write operations to untrusted users.
- Automatically create large numbers of Jira tickets during testing.

For testing, use a dedicated Jira project.

Before performing destructive or bulk Jira operations, obtain explicit approval.

Use least-privilege access wherever practical.

---

# 10. FIRST CODEX TASK

Start with **Phase 1, Step 1 only**.

Do the following:

1. Inspect my development environment.
2. Recommend the appropriate Python version and package manager.
3. Verify the current versions and compatibility of required libraries.
4. Propose a minimal project structure.
5. Explain how to configure Jira Cloud authentication securely.
6. Explain the commands required to create the project.
7. Set up the minimum environment required for Jira connectivity.
8. Explain every file created and its purpose.

Do not implement FastAPI, MCP or workflow simulation yet.

Do not generate the entire application.

Our first technical milestone is:

**Successfully authenticate with my real Jira Cloud account, retrieve my Jira projects and create one test Jira issue using Python.**

After completing the first milestone, explain what we built, how it works and how it will eventually integrate into HALO.

Then wait for my approval before continuing.