import pytest

from halo.cli import parser, run, subprocess_environment


async def test_cli_blocks_live_writes_before_any_request(settings):
    args = parser().parse_args(["create", "--project", "TEST", "--summary", "one"])
    with pytest.raises(ValueError, match="allow-live-write"):
        await run(args, settings)


def test_mcp_subprocess_does_not_receive_unrelated_credentials(settings, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "sensitive-github-token")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:8080")
    env = subprocess_environment(settings)
    assert "GH_TOKEN" not in env
    assert env["HTTPS_PROXY"] == "http://proxy.example:8080"
    assert env["JIRA_API_TOKEN"] == "test-secret"
