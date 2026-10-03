from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models import tables_ready

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    # Always 200 so the platform keeps the app running while the database is
    # still being onboarded; "database" says whether it is usable yet.
    return JSONResponse(
        {"status": "ok", "database": "ready" if tables_ready() else "waiting"}
    )
