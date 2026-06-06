"""Clerk-based authentication.

A single FastAPI dependency, ``require_user``, that verifies the incoming
Clerk session token and returns its claims. Endpoints depending on it are
protected; requests without a valid token get a 401.
"""

from typing import Any

import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import HTTPException, Request, status

from app.config import settings

_clerk = (
    Clerk(bearer_auth=settings.clerk_secret_key) if settings.clerk_secret_key else None
)


async def require_user(request: Request) -> dict[str, Any]:
    if _clerk is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk is not configured (CLERK_SECRET_KEY unset).",
        )

    # Clerk's SDK verifies against an httpx.Request; rebuild one from the
    # incoming request's method, URL and headers.
    httpx_request = httpx.Request(
        method=request.method,
        url=str(request.url),
        headers=request.headers.items(),
    )

    state = _clerk.authenticate_request(
        httpx_request,
        AuthenticateRequestOptions(),
    )

    if not state.is_signed_in or state.payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=state.reason.name if state.reason else "Not signed in",
        )

    return dict(state.payload)
