from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Note
from app.schemas import NoteInput, NoteResponse

router = APIRouter(prefix="/api/notes", tags=["notes"])
DbSession = Annotated[Session, Depends(get_db)]


def get_note_or_404(note_id: int, db: Session) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    return note


@router.get("", response_model=list[NoteResponse])
def list_notes(db: DbSession) -> list[Note]:
    try:
        return list(db.scalars(select(Note).order_by(Note.updated_at.desc())))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Unable to load notes.") from exc


@router.get("/{note_id}", response_model=NoteResponse)
def read_note(note_id: int, db: DbSession) -> Note:
    return get_note_or_404(note_id, db)


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteInput, db: DbSession) -> Note:
    try:
        note = Note(**payload.model_dump())
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to save note.") from exc


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, payload: NoteInput, db: DbSession) -> Note:
    note = get_note_or_404(note_id, db)
    try:
        note.title = payload.title
        note.content = payload.content
        db.commit()
        db.refresh(note)
        return note
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update note.") from exc


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: DbSession) -> None:
    note = get_note_or_404(note_id, db)
    try:
        db.delete(note)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to delete note.") from exc
