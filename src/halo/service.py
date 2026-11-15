"""Reusable Jira operations; adapters contain no Jira request-building logic."""

from pydantic import TypeAdapter

from halo.client import JiraClient
from halo.errors import JiraError
from halo.models import IssueCreate, IssueKey, IssueUpdate, ProjectKey, Search, adf


class JiraService:
    def __init__(self, client: JiraClient):
        self.client = client

    @staticmethod
    def issue_key(key: str) -> str:
        return TypeAdapter(IssueKey).validate_python(key)

    async def current_user(self) -> dict:
        return await self.client.request("GET", "/rest/api/3/myself")

    async def projects(self, start_at: int = 0, max_results: int = 50) -> dict:
        if start_at < 0 or not 1 <= max_results <= 100:
            raise ValueError("Invalid project pagination")
        return await self.client.request(
            "GET",
            "/rest/api/3/project/search",
            params={"startAt": start_at, "maxResults": max_results},
        )

    async def project(self, key: str) -> dict:
        key = TypeAdapter(ProjectKey).validate_python(key)
        return await self.client.request("GET", f"/rest/api/3/project/{key}")

    async def create_issue(self, data: IssueCreate) -> dict:
        fields = {
            "project": {"key": data.project_key},
            "summary": data.summary,
            "issuetype": {"name": data.issue_type},
        }
        if data.description is not None:
            fields["description"] = adf(data.description)
        # Jira issue creation has no generic idempotency guarantee. Never retry writes here.
        return await self.client.request("POST", "/rest/api/3/issue", json={"fields": fields})

    async def get_issue(self, key: str) -> dict:
        return await self.client.request(
            "GET",
            f"/rest/api/3/issue/{self.issue_key(key)}",
            params={"fields": "summary,description,status,issuetype,project"},
        )

    async def update_issue(self, key: str, data: IssueUpdate) -> dict:
        fields = data.model_dump(exclude_none=True)
        if data.description is not None:
            fields["description"] = adf(data.description)
        await self.client.request(
            "PUT", f"/rest/api/3/issue/{self.issue_key(key)}", json={"fields": fields}
        )
        return {"key": key, "updated": True}

    async def transitions(self, key: str) -> dict:
        return await self.client.request(
            "GET", f"/rest/api/3/issue/{self.issue_key(key)}/transitions"
        )

    async def transition(self, key: str, transition_id: str) -> dict:
        from halo.models import Transition

        transition_id = Transition(transition_id=transition_id).transition_id
        available = await self.transitions(key)
        if transition_id not in {str(t["id"]) for t in available.get("transitions", [])}:
            raise JiraError("Transition is not currently allowed for this issue", 409)
        await self.client.request(
            "POST",
            f"/rest/api/3/issue/{self.issue_key(key)}/transitions",
            json={"transition": {"id": transition_id}},
        )
        return {"key": key, "transitioned": True}

    async def transition_to(self, key: str, status: str) -> dict:
        issue = await self.get_issue(key)
        if issue["fields"]["status"]["name"].casefold() == status.casefold():
            return {"key": key, "already_in_status": True}
        transitions = await self.transitions(key)
        matches = [
            t
            for t in transitions.get("transitions", [])
            if t.get("to", {}).get("name", "").casefold() == status.casefold()
        ]
        if len(matches) != 1:
            raise JiraError("No unique allowed transition to the configured workflow status", 409)
        return await self.transition(key, str(matches[0]["id"]))

    async def add_comment(self, key: str, body: str) -> dict:
        from halo.models import Comment

        body = Comment(body=body).body
        return await self.client.request(
            "POST", f"/rest/api/3/issue/{self.issue_key(key)}/comment", json={"body": adf(body)}
        )

    async def search(self, data: Search) -> dict:
        payload = {
            "jql": data.jql,
            "maxResults": data.max_results,
            "fields": ["summary", "status", "issuetype", "project"],
        }
        if data.next_page_token is not None:
            payload["nextPageToken"] = data.next_page_token
        # Enhanced JQL search replaces the retired /search endpoint.
        return await self.client.request("POST", "/rest/api/3/search/jql", json=payload)
