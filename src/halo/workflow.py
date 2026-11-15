"""Small durable workflow simulator, with an explicit human approval boundary."""

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Annotated

from pydantic import Field, StringConstraints

from halo.errors import WorkflowConflict
from halo.gateways import Gateway
from halo.models import InputModel, ProjectKey, Summary

RunId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")]


class WorkflowSpec(InputModel):
    run_id: RunId
    project_key: ProjectKey
    summary: Summary = "HALO integration demonstration"
    development_status: str = Field(default="In Progress", min_length=1, max_length=100)
    testing_status: str | None = Field(default=None, min_length=1, max_length=100)
    done_status: str = Field(default="Done", min_length=1, max_length=100)
    test_failed: bool = False


class RunStore:
    def __init__(self, path: str):
        parent = Path(path).parent
        parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        os.chmod(path, 0o600)
        self.db.execute("""CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT NOT NULL,
            data TEXT NOT NULL)""")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def get(self, run_id: str) -> dict | None:
        row = self.db.execute("SELECT data FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def claim(self, spec: WorkflowSpec, route: str, target: str) -> tuple[dict, bool]:
        spec_data = spec.model_dump()
        fingerprint = hashlib.sha256(
            json.dumps(
                {"spec": spec_data, "route": route, "target": target}, sort_keys=True
            ).encode()
        ).hexdigest()
        data = {
            "run_id": spec.run_id,
            "state": "running",
            "route": route,
            "target": target,
            "spec": spec_data,
            "issue_key": None,
            "bug_key": None,
            "events": ["workflow_started"],
        }
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO runs VALUES (?, ?, ?, ?)",
                    (spec.run_id, fingerprint, "running", json.dumps(data)),
                )
            return data, True
        except sqlite3.IntegrityError:
            existing = self.db.execute(
                "SELECT fingerprint FROM runs WHERE run_id=?", (spec.run_id,)
            ).fetchone()[0]
            if existing != fingerprint:
                raise WorkflowConflict(
                    "Run ID already exists with different inputs or route"
                ) from None
            data = self.get(spec.run_id)
            if data["state"] in ("running", "needs_review"):
                raise WorkflowConflict(
                    "Run is active or uncertain; inspect Jira before recovery"
                ) from None
            return data, False

    def save(self, data: dict) -> None:
        with self.db:
            self.db.execute(
                "UPDATE runs SET state=?, data=? WHERE run_id=?",
                (data["state"], json.dumps(data), data["run_id"]),
            )

    def claim_approval(self, run_id: str, route: str, target: str) -> dict:
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            data = self.get(run_id)
            if not data:
                raise WorkflowConflict("Unknown workflow execution ID")
            if data["route"] != route:
                raise WorkflowConflict("Approval must use the original route")
            if data["target"] != target:
                raise WorkflowConflict("Approval must use the original Jira site and account")
            if data["state"] == "completed":
                return data
            if data["state"] != "awaiting_approval":
                raise WorkflowConflict("Only an awaiting_approval run can be approved")
            data["state"] = "running"
            self.db.execute(
                "UPDATE runs SET state=?, data=? WHERE run_id=?",
                ("running", json.dumps(data), run_id),
            )
            return data


class Workflow:
    def __init__(self, gateway: Gateway, store: RunStore, route: str, target: str = "local-test"):
        self.gateway, self.store, self.route, self.target = gateway, store, route, target

    async def move(self, key: str, status: str) -> None:
        issue = await self.gateway.call("get_issue", {"issue_key": key})
        if issue["fields"]["status"]["name"].casefold() == status.casefold():
            return
        available = await self.gateway.call("get_transitions", {"issue_key": key})
        matches = [
            t
            for t in available["transitions"]
            if t.get("to", {}).get("name", "").casefold() == status.casefold()
        ]
        if len(matches) != 1:
            raise WorkflowConflict("No unique allowed transition to the configured stage status")
        await self.gateway.call(
            "transition_issue", {"issue_key": key, "transition_id": str(matches[0]["id"])}
        )

    async def run(self, spec: WorkflowSpec) -> dict:
        data, claimed = self.store.claim(spec, self.route, self.target)
        if not claimed:
            return data
        try:
            result = await self.gateway.call(
                "create_issue",
                {
                    "project_key": spec.project_key,
                    "summary": spec.summary,
                    "issue_type": "Task",
                    "description": f"HALO workflow execution: {spec.run_id}",
                },
            )
            data["issue_key"] = result["key"]
            data["events"].append("task_created")
            self.store.save(data)  # Record the Jira key immediately after creation.
            await self.move(result["key"], spec.development_status)
            data["events"].append("development_started")
            self.store.save(data)
            if spec.testing_status:
                await self.move(result["key"], spec.testing_status)
            data["events"].append("testing_failed" if spec.test_failed else "testing_passed")
            if spec.test_failed:
                bug = await self.gateway.call(
                    "create_issue",
                    {
                        "project_key": spec.project_key,
                        "summary": f"HALO test failure: {spec.run_id}",
                        "issue_type": "Bug",
                        "description": f"Related workflow task: {result['key']}",
                    },
                )
                data["bug_key"] = bug["key"]
                self.store.save(data)
            await self.gateway.call(
                "add_comment",
                {
                    "issue_key": result["key"],
                    "body": f"Workflow {spec.run_id}: awaiting explicit human approval.",
                },
            )
            data["state"] = "awaiting_approval"
            data["events"].append("human_approval_required")
            self.store.save(data)
            return data
        except Exception:
            # An upstream timeout may have followed a successful write. Never auto-replay.
            data["state"] = "needs_review"
            data["events"].append("operation_failed_or_uncertain")
            self.store.save(data)
            raise

    async def approve(self, run_id: str) -> dict:
        data = self.store.claim_approval(run_id, self.route, self.target)
        if data["state"] == "completed":
            return data
        try:
            await self.move(data["issue_key"], data["spec"]["done_status"])
            data["state"] = "completed"
            data["events"].extend(["human_approved", "workflow_completed"])
            self.store.save(data)
            return data
        except Exception:
            data["state"] = "needs_review"
            data["events"].append("approval_operation_failed_or_uncertain")
            self.store.save(data)
            raise
