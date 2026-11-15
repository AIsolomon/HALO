"""Read and validate local configuration without exposing secrets."""

from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=False, hide_input_in_errors=True
    )

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: SecretStr = SecretStr("")
    jira_project_key: str = ""
    halo_api_key: SecretStr = SecretStr("")
    halo_demo: bool = False
    halo_timeout_seconds: float = Field(default=15, gt=0, le=120)
    halo_workflow_db: str = "work/workflows.sqlite3"

    @model_validator(mode="after")
    def validate_connection(self) -> "Settings":
        url = urlsplit(self.jira_base_url)
        if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise ValueError("JIRA_BASE_URL must be a site origin without credentials or path")
        if self.halo_demo:
            if url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost", "::1"):
                raise ValueError("Demo mode requires a loopback HTTP Jira simulator")
        elif (
            url.scheme != "https"
            or not url.hostname
            or not url.hostname.endswith(".atlassian.net")
            or url.port not in (None, 443)
        ):
            raise ValueError("Use your HTTPS Jira Cloud site, e.g. https://your-site.atlassian.net")
        if not self.jira_email or not self.jira_api_token.get_secret_value():
            raise ValueError(
                "Set JIRA_EMAIL and JIRA_API_TOKEN locally; never paste tokens into chat"
            )
        self.jira_base_url = self.jira_base_url.rstrip("/")
        return self
