from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


RUN_READ = "runs:read"
RUN_CREATE = "runs:create"
RUN_APPROVE = "runs:approve"
RUN_CANCEL = "runs:cancel"


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    permissions: frozenset[str]


class DemoTokenAuthenticator:
    """Deterministic teaching authenticator.

    Real deployments should validate signed tokens or call an identity provider.
    The important contract here is that tenant scope comes from authenticated
    identity, not from an arbitrary client-supplied tenant header.
    """

    def __init__(self, tokens: dict[str, Principal] | None = None) -> None:
        self._tokens = tokens or {
            "demo-owner-a": Principal(
                subject="user-owner-a",
                tenant_id="tenant-a",
                permissions=frozenset({RUN_READ, RUN_CREATE, RUN_APPROVE, RUN_CANCEL}),
            ),
            "demo-viewer-a": Principal(
                subject="user-viewer-a",
                tenant_id="tenant-a",
                permissions=frozenset({RUN_READ}),
            ),
            "demo-owner-b": Principal(
                subject="user-owner-b",
                tenant_id="tenant-b",
                permissions=frozenset({RUN_READ, RUN_CREATE, RUN_APPROVE, RUN_CANCEL}),
            ),
        }

    def authenticate(self, token: str) -> Principal:
        principal = self._tokens.get(token)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return principal


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    bearerFormat="opaque-demo-token",
    description="Teaching bearer auth. Production should validate real identity-provider tokens.",
)


def get_authenticator(request: Request) -> DemoTokenAuthenticator:
    return request.app.state.authenticator


AuthenticatorDep = Annotated[DemoTokenAuthenticator, Depends(get_authenticator)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Security(bearer_scheme),
]


async def get_current_principal(
    credentials: BearerCredentials,
    authenticator: AuthenticatorDep,
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authenticator.authenticate(credentials.credentials)


PrincipalDep = Annotated[Principal, Depends(get_current_principal)]


def require_permission(permission: str):
    async def dependency(principal: PrincipalDep) -> Principal:
        if permission not in principal.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing permission: {permission}",
            )
        return principal

    return dependency


RunReadPrincipal = Annotated[Principal, Depends(require_permission(RUN_READ))]
RunCreatePrincipal = Annotated[Principal, Depends(require_permission(RUN_CREATE))]
RunApprovePrincipal = Annotated[Principal, Depends(require_permission(RUN_APPROVE))]
RunCancelPrincipal = Annotated[Principal, Depends(require_permission(RUN_CANCEL))]
