import httpx
import pytest
from pydantic import ValidationError

from halo.client import JiraClient
from halo.config import Settings
from halo.errors import JiraError
from halo.models import IssueCreate, IssueUpdate, Search, adf
from halo.service import JiraService


async def test_create_update_comment_and_enhanced_search(settings):
    seen = []

    def handle(request):
        import json

        seen.append((request.method, request.url.path, json.loads(request.content or b"{}")))
        return httpx.Response(201, json={"key": "TEST-1"})

    client = JiraClient(settings, httpx.MockTransport(handle))
    service = JiraService(client)
    result = await service.create_issue(
        IssueCreate(project_key="TEST", summary="First task", description="Line 1\nLine 2")
    )
    await service.update_issue("TEST-1", IssueUpdate(description="Updated"))
    await service.add_comment("TEST-1", "A comment")
    await service.search(Search(jql="project = TEST", next_page_token="page2"))
    await client.close()
    assert result["key"] == "TEST-1"
    assert seen[0][2]["fields"]["description"] == adf("Line 1\nLine 2")
    assert seen[1][2] == {"fields": {"description": adf("Updated")}}
    assert seen[2][2] == {"body": adf("A comment")}
    assert seen[3][1] == "/rest/api/3/search/jql"
    assert seen[3][2]["nextPageToken"] == "page2"


@pytest.mark.parametrize("code", [401, 403, 404, 429, 500, 302])
async def test_safe_upstream_errors(settings, code):
    client = JiraClient(
        settings,
        httpx.MockTransport(
            lambda req: httpx.Response(
                code, text="test-secret upstream dump", headers={"Retry-After": "30"}
            )
        ),
    )
    with pytest.raises(JiraError) as exc:
        await JiraService(client).current_user()
    assert "test-secret" not in str(exc.value)
    assert exc.value.status_code == (code if code in (401, 403, 404, 429) else 502)
    await client.close()


async def test_get_retries_but_never_post(settings):
    calls = []

    def handle(request):
        calls.append(request.method)
        return httpx.Response(503, headers={"Retry-After": "0"})

    client = JiraClient(settings, httpx.MockTransport(handle))
    with pytest.raises(JiraError):
        await client.request("GET", "/rest/api/3/myself")
    with pytest.raises(JiraError):
        await client.request("POST", "/rest/api/3/issue", json={})
    assert calls == ["GET", "GET", "GET", "POST"]
    await client.close()


async def test_timeout_is_sanitized(settings):
    def handle(request):
        raise httpx.ReadTimeout("test-secret", request=request)

    client = JiraClient(settings, httpx.MockTransport(handle))
    with pytest.raises(JiraError, match="timed out") as exc:
        await JiraService(client).current_user()
    assert "test-secret" not in str(exc.value)
    await client.close()


async def test_transition_rejects_unavailable_id(settings):
    seen = []

    def handle(request):
        seen.append(request.method)
        return httpx.Response(200, json={"transitions": [{"id": "11"}]})

    client = JiraClient(settings, httpx.MockTransport(handle))
    with pytest.raises(JiraError, match="not currently allowed"):
        await JiraService(client).transition("TEST-1", "99")
    assert seen == ["GET"]
    await client.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://test.atlassian.net",
        "https://evil.test",
        "https://user:secret@test.atlassian.net",
        "https://test.atlassian.net/path",
    ],
)
def test_unsafe_live_urls_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jira_base_url=url, jira_email="a", jira_api_token="secret")


def test_inputs_reject_traversal_and_empty_updates():
    with pytest.raises(ValidationError):
        IssueCreate(project_key="../admin", summary="test")
    with pytest.raises(ValidationError):
        IssueUpdate()
    with pytest.raises(ValidationError):
        IssueCreate(project_key="TEST", summary="   ")
    with pytest.raises(ValidationError):
        Search(jql="project = TEST", max_results=1000)


@pytest.mark.parametrize("content", [b"not json", b"[]"])
async def test_invalid_response_shape_is_safe(settings, content):
    client = JiraClient(
        settings, httpx.MockTransport(lambda req: httpx.Response(200, content=content))
    )
    with pytest.raises(JiraError):
        await JiraService(client).current_user()
    await client.close()


async def test_api_requires_a_nontrivial_key(settings):
    from halo.api import create_app

    settings.halo_api_key = type(settings.halo_api_key)("short")
    with pytest.raises(ValueError, match="HALO_API_KEY"):
        create_app(settings)


async def test_http_date_retry_after_is_respected_without_early_retry(settings):
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(429, headers={"Retry-After": "Wed, 01 Jan 2100 00:00:00 GMT"})

    client = JiraClient(settings, httpx.MockTransport(handle))
    with pytest.raises(JiraError) as exc:
        await JiraService(client).current_user()
    assert exc.value.status_code == 429
    assert len(seen) == 1
    await client.close()


def test_startup_validation_hides_malformed_setting_input():
    with pytest.raises(ValidationError) as exc:
        Settings(
            _env_file=None,
            jira_base_url="https://user:sentinel-url-secret@test.atlassian.net",
            jira_email="user@example.com",
            jira_api_token="sentinel-token-secret",
        )
    assert "sentinel-url-secret" not in str(exc.value)
    assert "sentinel-token-secret" not in str(exc.value)
