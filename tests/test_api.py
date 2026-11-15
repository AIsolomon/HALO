import httpx

from halo.api import create_app
from halo.client import JiraClient
from halo.service import JiraService


async def test_rest_auth_validation_and_shared_service(settings):
    upstream_calls = []

    def jira(request):
        upstream_calls.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={"key": "TEST-1"})
        return httpx.Response(200, json={"displayName": "Demo user"})

    client = JiraClient(settings, httpx.MockTransport(jira))
    app = create_app(settings, JiraService(client))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api:
        assert (await api.get("/health")).status_code == 200
        assert (await api.get("/jira/me")).status_code == 401
        assert not upstream_calls
        headers = {"X-HALO-API-Key": "test-api-key"}
        response = await api.get("/jira/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["displayName"] == "Demo user"
        assert response.headers["X-Correlation-ID"]
        response = await api.post(
            "/jira/issues", headers=headers, json={"project_key": "TEST", "summary": "via REST"}
        )
        assert response.status_code == 201
        assert response.json()["key"] == "TEST-1"
        response = await api.put("/jira/issues/TEST-1", headers=headers, json={})
        assert response.status_code == 422
        assert len(upstream_calls) == 2
    await client.close()


async def test_rest_sanitizes_jira_errors(settings):
    client = JiraClient(
        settings, httpx.MockTransport(lambda req: httpx.Response(401, text="test-secret"))
    )
    app = create_app(settings, JiraService(client))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api:
        response = await api.get("/jira/me", headers={"X-HALO-API-Key": "test-api-key"})
        assert response.status_code == 401
        assert "test-secret" not in response.text
    await client.close()
