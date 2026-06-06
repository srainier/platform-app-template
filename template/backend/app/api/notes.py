"""Database demo: write and read notes from Postgres."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Note
from app.telemetry import get_tracer

router = APIRouter()


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    author: str = "anonymous"


class NoteOut(BaseModel):
    id: int
    author: str
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/notes", response_model=NoteOut)
async def create_note(
    body: NoteIn,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Note:
    with get_tracer().start_as_current_span("create_note") as span:
        note = Note(text=body.text, author=body.author)
        db.add(note)
        await db.commit()
        await db.refresh(note)
        span.set_attribute("note.id", note.id)
        return note


@router.get("/notes", response_model=list[NoteOut])
async def list_notes(db: Annotated[AsyncSession, Depends(get_db)]) -> list[Note]:
    result = await db.execute(select(Note).order_by(Note.id.desc()).limit(50))
    return list(result.scalars().all())
