import pytest

from halo.errors import WorkflowConflict
from halo.workflow import RunStore, Workflow, WorkflowSpec


class FakeGateway:
    def __init__(self):
        self.issues = {}
        self.calls = []
        self.fail_create = False

    async def call(self, operation, data):
        self.calls.append((operation, data))
        if operation == "create_issue":
            key = f"TEST-{len(self.issues) + 1}"
            self.issues[key] = {"key": key, "fields": {"status": {"name": "To Do"}}}
            if self.fail_create:
                raise TimeoutError("Simulate write succeeding before a lost response")
            return {"key": key}
        key = data["issue_key"]
        if operation == "get_issue":
            return self.issues[key]
        if operation == "get_transitions":
            return {
                "transitions": [
                    {"id": "21", "to": {"name": "In Progress"}},
                    {"id": "31", "to": {"name": "Done"}},
                ]
            }
        if operation == "transition_issue":
            self.issues[key]["fields"]["status"]["name"] = (
                "In Progress" if data["transition_id"] == "21" else "Done"
            )
        return {}


async def test_workflow_gate_persistence_and_replay(tmp_path):
    path = str(tmp_path / "runs.sqlite3")
    store = RunStore(path)
    gateway = FakeGateway()
    workflow = Workflow(gateway, store, "rest")
    spec = WorkflowSpec(run_id="one", project_key="TEST", test_failed=True)
    paused = await workflow.run(spec)
    assert paused["state"] == "awaiting_approval"
    assert paused["bug_key"] == "TEST-2"
    assert gateway.issues["TEST-1"]["fields"]["status"]["name"] == "In Progress"
    store.close()
    store = RunStore(path)
    workflow = Workflow(gateway, store, "rest")
    assert (await workflow.run(spec))["issue_key"] == "TEST-1"
    assert len(gateway.issues) == 2
    assert (await workflow.approve("one"))["state"] == "completed"
    calls = len(gateway.calls)
    assert (await workflow.approve("one"))["state"] == "completed"
    assert len(gateway.calls) == calls
    assert gateway.issues["TEST-1"]["fields"]["status"]["name"] == "Done"
    store.close()


async def test_uncertain_create_cannot_duplicate_on_retry(tmp_path):
    store = RunStore(str(tmp_path / "runs.sqlite3"))
    gateway = FakeGateway()
    gateway.fail_create = True
    workflow = Workflow(gateway, store, "mcp")
    spec = WorkflowSpec(run_id="uncertain", project_key="TEST")
    with pytest.raises(TimeoutError):
        await workflow.run(spec)
    assert store.get("uncertain")["state"] == "needs_review"
    with pytest.raises(WorkflowConflict, match="uncertain"):
        await workflow.run(spec)
    assert len(gateway.issues) == 1
    store.close()


async def test_run_id_conflict_and_route_mismatch(tmp_path):
    store = RunStore(str(tmp_path / "runs.sqlite3"))
    gateway = FakeGateway()
    workflow = Workflow(gateway, store, "rest")
    await workflow.run(WorkflowSpec(run_id="one", project_key="TEST"))
    with pytest.raises(WorkflowConflict, match="different inputs"):
        await workflow.run(WorkflowSpec(run_id="one", project_key="TEST", summary="changed"))
    with pytest.raises(WorkflowConflict, match="original route"):
        await Workflow(gateway, store, "mcp").approve("one")
    with pytest.raises(WorkflowConflict, match="Unknown"):
        await workflow.approve("missing")
    store.close()


async def test_unavailable_stage_needs_review(tmp_path):
    store = RunStore(str(tmp_path / "runs.sqlite3"))
    workflow = Workflow(FakeGateway(), store, "rest")
    with pytest.raises(WorkflowConflict, match="No unique"):
        await workflow.run(WorkflowSpec(run_id="bad", project_key="TEST", testing_status="QA"))
    assert store.get("bad")["state"] == "needs_review"
    assert store.get("bad")["issue_key"] == "TEST-1"
    store.close()


async def test_approval_cannot_target_another_jira_site(tmp_path):
    store = RunStore(str(tmp_path / "runs.sqlite3"))
    gateway = FakeGateway()
    workflow = Workflow(gateway, store, "rest", target="site-a|account-a")
    await workflow.run(WorkflowSpec(run_id="bound", project_key="TEST"))
    with pytest.raises(WorkflowConflict, match="original Jira site"):
        await Workflow(gateway, store, "rest", target="site-b|account-b").approve("bound")
    assert store.get("bound")["state"] == "awaiting_approval"
    store.close()
