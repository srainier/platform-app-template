import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db import engine

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Note(Base):
    """A trivial table to demonstrate Postgres read/write on the shared cluster.

    Delete this (and the /notes endpoints) once you start building real models.
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Clerk user id when the note is created by a signed-in user, else "anonymous".
    author: Mapped[str] = mapped_column(String(255), default="anonymous")
    text: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


async def create_tables() -> None:
    """Create tables if they don't exist.

    A real app would use Alembic migrations; for a starter this keeps the moving
    parts to a minimum. Note: the app's database user needs CREATE on the
    ``public`` schema for this to succeed on a fresh DO managed cluster (PG15+).
    See the post-deploy setup in the generated README.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_tables_ready = False


def tables_ready() -> bool:
    """True once ``create_tables`` has succeeded in this process."""
    return _tables_ready


async def ensure_tables(max_delay: float = 60.0) -> None:
    """Create tables, retrying in the background until the database lets us in.

    On a brand-new app the database is unreachable until the platform admin
    onboards it (trusted source + schema grant). Retrying here instead of
    failing at startup lets the very first deploy succeed; the app then picks
    up the database on its own once onboarding is done, with no redeploy.
    """
    global _tables_ready
    delay = 2.0
    while True:
        try:
            await create_tables()
        except Exception as exc:  # noqa: BLE001 - any DB error means "not yet"
            logger.warning(
                "Database not ready (%s); retrying in %.0fs. A new app needs "
                "admin onboarding before it can reach the shared cluster.",
                type(exc).__name__,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)
        else:
            _tables_ready = True
            logger.info("Database ready; tables created")
            return
