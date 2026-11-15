"""Safe errors shared by CLI, REST, MCP, and workflows."""


class JiraError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.status_code = status_code
        super().__init__(message)


class WorkflowConflict(Exception):
    """A run cannot safely continue automatically."""
