"""Feature-flag demo: read a flag from Flagsmith.

The demo flag is ``hello_banner``. The endpoint never fails the request because
of the flag: if Flagsmith is unconfigured (no API key, e.g. local dev) OR the
flag does not exist yet in the Flagsmith environment, it reports the flag as
disabled rather than raising. Create the flag in the Flagsmith UI to flip it on.
"""

import logging
from typing import Any

from fastapi import APIRouter
from flagsmith import Flagsmith

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

FLAG_NAME = "hello_banner"

_flagsmith = (
    Flagsmith(environment_key=settings.flagsmith_api_key)
    if settings.flagsmith_api_key
    else None
)


@router.get("/feature")
async def feature() -> dict[str, Any]:
    if _flagsmith is None:
        return {
            "flag": FLAG_NAME,
            "enabled": False,
            "source": "default (Flagsmith unset)",
        }

    try:
        flags = _flagsmith.get_environment_flags()
        return {
            "flag": FLAG_NAME,
            "enabled": flags.is_feature_enabled(FLAG_NAME),
            "value": flags.get_feature_value(FLAG_NAME),
            "source": "flagsmith",
        }
    except Exception:
        # Most commonly the flag has not been created in Flagsmith yet. Degrade
        # to "disabled" instead of 500ing so the rest of the app keeps working.
        logger.warning("Flagsmith flag %r lookup failed; defaulting off", FLAG_NAME)
        return {
            "flag": FLAG_NAME,
            "enabled": False,
            "source": "default (flag missing or Flagsmith error)",
        }
