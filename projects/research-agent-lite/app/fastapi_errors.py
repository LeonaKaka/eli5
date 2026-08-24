from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ValidationIssue(BaseModel):
    location: str
    message: str
    type: str


class ProblemDetails(BaseModel):
    """Stable public error projection inspired by HTTP Problem Details.

    Internal exceptions, request bodies, stack traces and control-plane state are
    deliberately not part of this schema. `request_id` is safe correlation data
    that lets operators find richer private logs without leaking them to clients.
    """

    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    instance: str
    code: str
    request_id: str
    errors: list[ValidationIssue] | None = None


@dataclass(frozen=True)
class ApiProblem(Exception):
    status: int
    code: str
    title: str
    detail: str
    headers: dict[str, str] | None = None


_STATUS_DEFAULTS: dict[int, tuple[str, str]] = {
    400: ("bad_request", "Bad request"),
    401: ("authentication_required", "Authentication required"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Resource not found"),
    409: ("conflict", "Request conflict"),
    412: ("precondition_failed", "Precondition failed"),
    422: ("validation_error", "Request validation failed"),
    428: ("precondition_required", "Precondition required"),
    429: ("rate_limited", "Too many requests"),
    503: ("service_unavailable", "Service unavailable"),
}


def problem_responses(*statuses: int) -> dict[int, dict[str, Any]]:
    """OpenAPI declarations for the same public ProblemDetails contract."""

    return {
        status: {
            "model": ProblemDetails,
            "description": _STATUS_DEFAULTS.get(status, ("error", "Request failed"))[1],
            "content": {"application/problem+json": {}},
        }
        for status in statuses
    }


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if value:
        return str(value)
    value = f"req-{uuid4().hex}"
    request.state.request_id = value
    return value


def _problem(
    request: Request,
    *,
    status_code: int,
    detail: str,
    code: str | None = None,
    title: str | None = None,
    errors: list[ValidationIssue] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    default_code, default_title = _STATUS_DEFAULTS.get(
        status_code,
        ("internal_error" if status_code >= 500 else "request_error", "Internal server error" if status_code >= 500 else "Request failed"),
    )
    request_id = _request_id(request)
    body = ProblemDetails(
        type=f"urn:research-assistant:problem:{code or default_code}",
        title=title or default_title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        code=code or default_code,
        request_id=request_id,
        errors=errors,
    )
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
        headers=response_headers,
        media_type="application/problem+json",
    )


def install_error_layer(app: FastAPI) -> None:
    """Install request correlation plus stable public exception handlers."""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = f"req-{uuid4().hex}"
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request.state.request_id)
        return response

    @app.exception_handler(ApiProblem)
    async def api_problem_handler(request: Request, exc: ApiProblem):
        return _problem(
            request,
            status_code=exc.status,
            detail=exc.detail,
            code=exc.code,
            title=exc.title,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        issues = [
            ValidationIssue(
                location=".".join(str(part) for part in error.get("loc", ())),
                message=str(error.get("msg", "invalid value")),
                type=str(error.get("type", "validation_error")),
            )
            for error in exc.errors()
        ]
        return _problem(
            request,
            status_code=422,
            detail="One or more request fields are invalid.",
            code="validation_error",
            title="Request validation failed",
            errors=issues,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        return _problem(
            request,
            status_code=exc.status_code,
            detail=detail,
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Private telemetry/logging should capture repr(exc) with request_id.
        # Never return the exception string or traceback to the public client.
        return _problem(
            request,
            status_code=500,
            detail="An unexpected server error occurred.",
            code="internal_error",
            title="Internal server error",
        )
