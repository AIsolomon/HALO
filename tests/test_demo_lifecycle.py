"""Exercise real subprocess cleanup, including Windows inherited log handles."""

import httpx
import pytest

from halo import demo


def test_startup_failure_preserves_diagnostics_and_stops_server(tmp_path, monkeypatch):
    original_wait = demo.wait_ready
    urls = []

    def fail_after_ready(url, process, auth=None):
        original_wait(url, process, auth)
        urls.append((url, auth))
        with (tmp_path / "servers.log").open("a", encoding="utf-8") as log:
            log.write("Controlled startup diagnostic\n")
        raise RuntimeError("Controlled startup failure")

    monkeypatch.setattr(demo, "wait_ready", fail_after_ready)
    with pytest.raises(RuntimeError, match="Controlled startup failure") as exc:
        with demo.demo_environment(tmp_path):
            pytest.fail("An unready environment must not be yielded")
    assert "Controlled startup diagnostic" in "\n".join(exc.value.__notes__)
    # On Windows this fails if a surviving child still owns the inherited handle.
    (tmp_path / "servers.log").unlink()
    url, auth = urls[0]
    # A closed loopback port can time out on Windows instead of refusing immediately.
    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        httpx.get(url, auth=auth, timeout=1, trust_env=False)


def test_workflow_failure_closes_log_and_both_servers(tmp_path):
    with pytest.raises(ValueError, match="Controlled workflow failure"):
        with demo.demo_environment(tmp_path) as (api_url, env):
            jira_url = env["JIRA_BASE_URL"]
            raise ValueError("Controlled workflow failure")
    (tmp_path / "servers.log").unlink()
    for url in (f"{api_url}/health", f"{jira_url}/rest/api/3/myself"):
        with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
            httpx.get(url, timeout=1, trust_env=False)
