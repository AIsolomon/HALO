# Verified environment and dependencies

Inspection date: **16 November 2026**, using the user's client date. The execution
host clock was still 15 November UTC. This is a managed Codex Cloud computer; it
provides no information about the user's laptop OS or its sleep/lock configuration.

| Item | Observed |
| --- | --- |
| OS | Debian GNU/Linux 13, Linux x86_64 |
| Python | CPython 3.12.14 on host; 3.12.16 in container |
| Git | 2.52.0 |
| Package manager | uv 0.13.6, also verified available on PyPI |
| VS Code CLI | `code` not found on PATH; Codex workspace is available |
| Docker daemon | 29.9.2 at managed local socket |
| Repository | `/workspace/HALO`, branch `main` |
| GitHub identity | AIsolomon; initial creation denied; user-created AIsolomon/HALO later accessible |
| Jira configuration | No Jira environment variables or `.env`; no configured cloud secrets |

Python **3.12** is recommended for this project because it is installed, supported
by the selected packages, and exercised by the complete suite. The package permits
3.13 but it was not separately tested. Do not infer that this is the latest Python
release. `uv` creates a project virtual environment and uses the committed lockfile.

Direct versions were fetched from the live PyPI JSON API and were non-yanked stable
releases published by the requested date. The resolver checked compatibility and
selected transitive dependencies using the cutoff configured in `pyproject.toml`:
`2026-11-17T00:00:00Z`. This prevents accidentally selecting releases after the
16 November UTC date boundary. `uv.lock` preserves exact resolution and hashes.

| Package | Selected version | PyPI upload date |
| --- | --- | --- |
| httpx | 0.28.1 | 2024-12-06 |
| pydantic | 2.14.3 | 2026-11-05 |
| pydantic-settings | 2.16.3 | 2026-11-13 |
| fastapi | 0.163.1 | 2026-11-15 |
| uvicorn | 0.54.0 | 2026-09-25 |
| mcp | 2.3.0 | 2026-10-02 |
| pytest | 9.2.0 | 2026-10-27 |
| pytest-asyncio | 1.5.0 | 2026-11-12 |
| ruff | 0.17.5 | 2026-11-12 |

`uv sync --locked` verified that the lockfile matches the declared dependencies;
`uv pip check` verified compatibility of the installed environment. Tests verify
actual imports and execution, including the official MCP SDK v2 `MCPServer` and
`Client` APIs. A successful solve is not a security certification or proof that
all future Jira site configurations are compatible.

## Official references consulted

- [Jira basic authentication](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/)
- [Jira REST v3 issues](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)
- [Jira REST v3 comments](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-comments/)
- [Jira enhanced issue search](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [FastAPI first steps](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/)
- [uv projects](https://docs.astral.sh/uv/guides/projects/)
- [Official Atlassian MCP guide](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/)
- PyPI package metadata: `https://pypi.org/pypi/<package>/json`.

## Cloud-specific notes

The user's laptop is not controlled by these tools. No laptop power/lock setting
was changed. The cloud's default uv cache directory is read-only; installation
used `UV_CACHE_DIR=/workspace/work/uv-cache` instead of changing home permissions.

Docker's first build encountered the cloud proxy's certificate chain. Verification
used a temporary Dockerfile in `/workspace/work/` with the system certificate
bundle mounted as a BuildKit secret for pip/uv steps. TLS verification stayed on;
no proxy certificate was copied into the committed source or the final image.
On this cloud, repeating that build requires the same temporary trust adjustment.
