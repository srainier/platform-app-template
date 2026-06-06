from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db import engine


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
