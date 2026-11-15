"""Validated business inputs, independent of REST and MCP."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ProjectKey = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{1,49}$")]
IssueKey = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{1,49}-[1-9][0-9]*$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32767)]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IssueCreate(InputModel):
    project_key: ProjectKey
    summary: Summary
    issue_type: Literal["Task", "Story", "Bug"] = "Task"
    description: Text | None = None


class IssueUpdate(InputModel):
    summary: Summary | None = None
    description: Text | None = None

    @model_validator(mode="after")
    def require_change(self) -> "IssueUpdate":
        if self.summary is None and self.description is None:
            raise ValueError("Provide a summary or description")
        return self


class Comment(InputModel):
    body: Text


class Transition(InputModel):
    transition_id: Annotated[str, StringConstraints(pattern=r"^[0-9]+$")]


class Search(InputModel):
    jql: Text
    max_results: int = Field(default=25, ge=1, le=100)
    next_page_token: str | None = Field(default=None, max_length=4096)


def adf(text: str) -> dict:
    """Jira v3 rich text uses Atlassian Document Format, including for plain text."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": line}]}
            if line
            else {"type": "paragraph", "content": []}
            for line in text.split("\n")
        ],
    }
