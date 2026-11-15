"""Deliberately small, in-memory Jira HTTP simulator. Never a live Jira substitute."""

import os
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

DEMO_EMAIL = "demo@example.invalid"
DEMO_TOKEN = "demo-only-token"
DEMO_API_KEY = "demo-local-api-key"


def create_app() -> FastAPI:
    if os.environ.get("HALO_DEMO", "").lower() not in ("true", "1"):
        raise RuntimeError("The simulator requires HALO_DEMO=true")
    basic = HTTPBasic()
    issues: dict[str, dict] = {}
    comments: dict[str, list] = {}

    def authorize(credentials: Annotated[HTTPBasicCredentials, Depends(basic)]):
        if not (
            secrets.compare_digest(credentials.username, DEMO_EMAIL)
            and secrets.compare_digest(credentials.password, DEMO_TOKEN)
        ):
            raise HTTPException(401, "Demo authentication failed")

    app = FastAPI(title="HALO local Jira simulator", dependencies=[Depends(authorize)])

    def issue(key: str) -> dict:
        if key not in issues:
            raise HTTPException(404, "Unknown demo issue")
        return issues[key]

    def allowed(key: str) -> list:
        status = issue(key)["fields"]["status"]["name"]
        if status == "To Do":
            return [{"id": "21", "name": "Start progress", "to": {"name": "In Progress"}}]
        if status == "In Progress":
            return [{"id": "31", "name": "Complete", "to": {"name": "Done"}}]
        return []

    @app.get("/rest/api/3/myself")
    def myself():
        return {"accountId": "demo-user", "displayName": "HALO Demo User", "active": True}

    @app.get("/rest/api/3/project/search")
    def projects(startAt: int = 0, maxResults: int = 50):
        values = [{"id": "10000", "key": "TEST", "name": "HALO simulator project"}]
        page = values[startAt : startAt + maxResults]
        return {
            "values": page,
            "startAt": startAt,
            "maxResults": maxResults,
            "total": 1,
            "isLast": startAt + len(page) >= 1,
        }

    @app.get("/rest/api/3/project/{key}")
    def project(key: str):
        if key != "TEST":
            raise HTTPException(404, "Unknown demo project")
        return {"id": "10000", "key": "TEST", "name": "HALO simulator project"}

    @app.post("/rest/api/3/issue", status_code=201)
    def create_issue(data: dict):
        fields = data.get("fields", {})
        if fields.get("project", {}).get("key") != "TEST" or not fields.get("summary"):
            raise HTTPException(400, "Use project TEST and a summary in this simulator")
        key = f"TEST-{len(issues) + 1}"
        fields = {**fields, "status": {"name": "To Do"}}
        issues[key] = {"id": str(10000 + len(issues)), "key": key, "fields": fields}
        comments[key] = []
        return {"id": issues[key]["id"], "key": key}

    @app.get("/rest/api/3/issue/{key}")
    def get_issue(key: str):
        return issue(key)

    @app.put("/rest/api/3/issue/{key}", status_code=204)
    def update_issue(key: str, data: dict):
        issue(key)["fields"].update(data["fields"])
        return None

    @app.get("/rest/api/3/issue/{key}/transitions")
    def transitions(key: str):
        return {"transitions": allowed(key)}

    @app.post("/rest/api/3/issue/{key}/transitions", status_code=204)
    def transition(key: str, data: dict):
        found = [t for t in allowed(key) if t["id"] == data.get("transition", {}).get("id")]
        if not found:
            raise HTTPException(400, "Transition is not currently allowed")
        issue(key)["fields"]["status"] = found[0]["to"]
        return None

    @app.post("/rest/api/3/issue/{key}/comment", status_code=201)
    def comment(key: str, data: dict):
        issue(key)
        value = {"id": str(len(comments[key]) + 1), "body": data["body"]}
        comments[key].append(value)
        return value

    @app.post("/rest/api/3/search/jql")
    def search(data: dict):
        # Intentionally not a JQL parser: support only the demo project's basic query.
        if data.get("jql", "").strip().upper() != "PROJECT = TEST":
            raise HTTPException(400, "Simulator only supports: project = TEST")
        try:
            start = int(data.get("nextPageToken", "0"))
        except ValueError:
            raise HTTPException(400, "Invalid demo page token") from None
        size = min(max(int(data.get("maxResults", 25)), 1), 100)
        values = list(issues.values())
        result = {"issues": values[start : start + size], "isLast": start + size >= len(values)}
        if not result["isLast"]:
            result["nextPageToken"] = str(start + size)
        return result

    return app
