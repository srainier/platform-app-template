"""User-accounts demo: a Clerk-protected endpoint."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.auth import require_user

router = APIRouter()


UserClaims = Annotated[dict[str, Any], Depends(require_user)]


@router.get("/me")
async def me(claims: UserClaims) -> dict[str, Any]:
    """Return the signed-in user's id and session claims.

    Requires a valid Clerk session token in the Authorization header.
    """
    return {
        "user_id": claims.get("sub"),
        "session_id": claims.get("sid"),
        "claims": claims,
    }
