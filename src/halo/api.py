"""Local REST adapter. Bind to loopback; require an API key on business routes."""

import json
import logging
import secrets
import time
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from halo.client import JiraClient
from halo.config import Settings
from halo.errors import JiraError
from halo.models import Comment, IssueCreate, IssueKey, IssueUpdate, ProjectKey, Search, Transition
from halo.service import JiraService

logger = logging.getLogger("halo.audit")
api_key_header = APIKeyHeader(name="X-HALO-API-Key", auto_error=False)


def create_app(settings: Settings | None = None, service: JiraService | None = None) -> FastAPI:
    config = settings or Settings()
    if len(config.halo_api_key.get_secret_value()) < 12:
        raise ValueError("Set HALO_API_KEY locally to a random value of at least 12 characters")
    client = None if service else JiraClient(config)
    jira = service or JiraService(client)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if client:
            await client.close()

    async def authorize(key: Annotated[str | None, Security(api_key_header)]):
        if not secrets.compare_digest(key or "", config.halo_api_key.get_secret_value()):
            raise HTTPException(401, "A valid X-HALO-API-Key is required")

    app = FastAPI(title="HALO Jira Integration", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def audit(request: Request, call_next):
        correlation_id = str(uuid4())  # Do not trust arbitrary user strings in logs.
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        # No bodies, query strings, headers, email addresses, or issue contents in logs.
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "route": getattr(route, "path", "unmatched"),
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                }
            )
        )
        return response

    @app.exception_handler(JiraError)
    async def jira_error(request: Request, exc: JiraError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "mode": "demo" if config.halo_demo else "live",
            "jira_verified": False,
        }

    auth = [Depends(authorize)]

    @app.get("/jira/me", dependencies=auth)
    async def me():
        return await jira.current_user()

    @app.get("/jira/projects", dependencies=auth)
    async def projects(start_at: int = Query(0, ge=0), max_results: int = Query(50, ge=1, le=100)):
        return await jira.projects(start_at, max_results)

    @app.get("/jira/projects/{key}", dependencies=auth)
    async def project(key: ProjectKey):
        return await jira.project(key)

    @app.post("/jira/issues", status_code=201, dependencies=auth)
    async def create_issue(data: IssueCreate):
        return await jira.create_issue(data)

    @app.get("/jira/issues/{key}", dependencies=auth)
    async def get_issue(key: IssueKey):
        return await jira.get_issue(key)

    @app.put("/jira/issues/{key}", dependencies=auth)
    async def update_issue(key: IssueKey, data: IssueUpdate):
        return await jira.update_issue(key, data)

    @app.get("/jira/issues/{key}/transitions", dependencies=auth)
    async def transitions(key: IssueKey):
        return await jira.transitions(key)

    @app.post("/jira/issues/{key}/transitions", dependencies=auth)
    async def transition(key: IssueKey, data: Transition):
        return await jira.transition(key, data.transition_id)

    @app.post("/jira/issues/{key}/comments", status_code=201, dependencies=auth)
    async def comment(key: IssueKey, data: Comment):
        return await jira.add_comment(key, data.body)

    @app.post("/jira/search", dependencies=auth)
    async def search(data: Search):
        return await jira.search(data)

    return app
