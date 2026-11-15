# HALO development instructions

Read `docs/PROJECT_BRIEF.md`, `TASKS.md`, and `DECISIONS.md` before making changes.

- The original brief starts with Phase 1, Step 1. The user subsequently authorized
  an unattended end-to-end local implementation. That build may proceed across
  phases with simulator validation; do not label untested live Jira as complete.
- For further work, implement small, explained increments.
- Complete and validate each phase before starting the next; obtain the user's
  approval before advancing to another major phase.
- Inspect existing files and explain intended changes before editing.
- Teach the purpose, important syntax, execution flow, verification commands,
  troubleshooting, and architecture of each implemented module.
- Ask one or two understanding questions before the next major module.
- Keep Jira logic framework-independent and shared by future REST and MCP adapters.
- Prefer Python, HTTPX, and uv; verify current stable package versions and
  compatibility using official sources before installation. Do not invent versions.
- Use type hints and descriptive names; avoid unnecessary abstractions.
- Run relevant checks and report results. Use real Jira for integration validation
  when configured; never claim a live check based on mocks alone.
- Protect credentials from the first prototype. Never commit `.env`, hardcode or
  log tokens, request tokens in chat, or distribute Jira credentials to desktops.
- Configure HTTP timeouts and safe error handling from Phase 1.
- Use a dedicated Jira test project. Obtain explicit approval before destructive
  or bulk Jira operations; do not create large numbers of test tickets.
- Maintain `TASKS.md` and document material decisions in `DECISIONS.md`.
- REST, MCP, workflows, and baseline hardening now have local implementations.
  Review `docs/HANDOFF.md` for real-account and enterprise work still outstanding.
