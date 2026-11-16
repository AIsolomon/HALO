# Load HALO on your laptop in VS Code

Clone the source from:
https://github.com/AIsolomon/HALO

The project currently runs in a cloud workspace. Your laptop receives its own copy
when you clone the repository. Cloud `.venv`, private `.env`, reports, and local
workflow databases are not part of the source transfer.

## 1. Check the laptop prerequisites

Install Git, Python 3.12, VS Code, and VS Code's Python extension if missing. Open a
terminal on your laptop. These commands report the installed versions; they do not
change files.

```bash
git --version
python --version
```

On Windows, if `python` is unavailable, try `py -3.12 --version`. The project was
tested with Python 3.12. Keep using that version for the first run.

## 2. Clone and open the folder

In VS Code, press **Ctrl+Shift+P** (Mac: **Cmd+Shift+P**), choose **Git: Clone**,
paste the following URL, and select a normal local project folder:

```text
https://github.com/AIsolomon/HALO.git
```

Sign into the GitHub account that has access if prompted, then choose **Open**.
If this repository is private, the browser and VS Code must both have account
access. Avoid cloning into an existing HALO folder containing other work.

Alternatively, in a terminal, `git clone` downloads source plus Git history and
`cd` selects the resulting project folder:

```bash
git clone https://github.com/AIsolomon/HALO.git
cd HALO
```

Then use **File -> Open Folder** in VS Code and select that HALO folder.

## 3. Install the project environment

Choose **Terminal -> New Terminal** in VS Code. Confirm it is in the folder that
contains `pyproject.toml`. The first command installs the verified uv package
manager; the second creates `.venv` and installs the exact locked dependencies.

```bash
python -m pip install uv==0.13.6
uv sync --frozen
```

On Windows, use `py -3.12 -m pip install uv==0.13.6` if required. If `uv` is not on
PATH yet, reopen the terminal, or use `python -m uv` (Windows: `py -3.12 -m uv`)
instead of `uv` in the remaining commands.

In VS Code's command palette choose **Python: Select Interpreter**, then the
interpreter under HALO's `.venv`. It is `.venv/Scripts/python.exe` on Windows or
`.venv/bin/python` on macOS/Linux. You do not need to activate it manually when
using `uv run`.

## 4. Run the complete simulator first

This starts temporary local Jira-simulator and REST servers, launches an MCP
client/server connection, exercises both routes, and stops those processes.
It requires no Jira credentials or HALO API key and creates no real Jira tickets.

```bash
uv run --frozen halo demo
```

Expected JSON: `rest.state` and `mcp.state` both say `completed`, ten MCP tools are
listed, and `live_jira_verified` is `false`. That last value is correct because this
run uses simulated Jira. An intentionally rejected invalid-input test may print a
safe MCP tool-error line before the successful JSON.

## 5. Run tests

The following command checks behavior and safety, including actual local REST
and MCP transports. It does not contact your real Jira account.

```bash
uv run --frozen pytest -q
```

Expected result for this version: **30 passed**. For optional style checks, run:

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
```

## 6. Configure real Jira only after the simulator passes

In VS Code's Explorer, copy `.env.example` and name the copy `.env`. Edit `.env`
locally with your development Jira site, email, token, and dedicated project key.
Never send the token in chat. `.env` is excluded from Git.

`HALO_API_KEY` is a separate password you create for your own REST API; Atlassian
does not issue it. This command generates a random value locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

On Windows you may use `py -3.12` instead of `python`. Copy the generated text into
the `HALO_API_KEY=` line in `.env`. Keep `HALO_DEMO=false` for the real Jira site.
Then perform a read-only authentication/project check:

```bash
uv run --frozen halo check
```

Expect your Jira display name and visible projects. This does not create issues.
Follow `docs/SETUP.md` for the first real test issue and further operations.

## 7. Open the REST API in your laptop browser

This command starts a persistent local server. Leave the terminal open:

```bash
uv run --frozen halo serve
```

After the terminal reports that the server is running, open:
http://127.0.0.1:8000/docs

That is a laptop-local address, not a published website. Click **Authorize** and
enter your generated **HALO_API_KEY**, not the Jira API token. Try the read-only
`GET /jira/me` endpoint first. Press Ctrl+C in the terminal to stop the server.

## Troubleshooting

- **Repository not found:** confirm the exact URL and GitHub account access. Cloud
  access may need to be refreshed if the repository visibility changes.
- **No pyproject.toml:** open HALO's project root, not its parent folder.
- **uv not recognized:** reopen the terminal or use `python -m uv` as described above.
- **Invalid settings:** check `.env` locally; do not paste secret values into chat.
- **localhost refuses connection:** the server must be running on this laptop. The
  demo stops its servers when it finishes; use `halo serve` for Swagger.
- **HALO returns 401:** Swagger requires the locally generated HALO key.
- **Jira rejects authentication:** verify the separate Jira email/token and expiry.
