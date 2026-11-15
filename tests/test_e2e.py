from halo.demo import run_demo


async def test_rest_and_mcp_end_to_end_over_real_local_transports():
    report = await run_demo()
    assert report["mode"] == "local_simulator"
    assert report["live_jira_verified"] is False
    assert report["rest"]["state"] == report["mcp"]["state"] == "completed"
    assert report["rest"]["duplicate_prevention"] == "passed"
    assert len(report["mcp"]["discovered_tools"]) == 10
