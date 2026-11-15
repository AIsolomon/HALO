import pytest

from halo.config import Settings


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        jira_base_url="https://test.atlassian.net",
        jira_email="dev@example.com",
        jira_api_token="test-secret",
        jira_project_key="TEST",
        halo_api_key="test-api-key",
    )
