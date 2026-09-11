from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Note, User
from app.schemas import NoteInput, NoteResponse

router = APIRouter(prefix="/api/notes", tags=["notes"])
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_note_or_404(note_id: int, current_user: User, db: Session) -> Note:
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    return note


@router.get("", response_model=list[NoteResponse])
def list_notes(current_user: CurrentUser, db: Session = Depends(get_db)) -> list[Note]:
    try:
        return list(db.scalars(select(Note).where(Note.user_id == current_user.id).order_by(Note.updated_at.desc())))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Unable to load notes.") from exc


@router.get("/{note_id}", response_model=NoteResponse)
def read_note(note_id: int, current_user: CurrentUser, db: Session = Depends(get_db)) -> Note:
    return get_note_or_404(note_id, current_user, db)


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteInput, current_user: CurrentUser, db: Session = Depends(get_db)) -> Note:
    try:
        note = Note(**payload.model_dump(), user_id=current_user.id)
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to save note.") from exc


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, payload: NoteInput, current_user: CurrentUser, db: Session = Depends(get_db)) -> Note:
    note = get_note_or_404(note_id, current_user, db)
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
def delete_note(note_id: int, current_user: CurrentUser, db: Session = Depends(get_db)) -> None:
    note = get_note_or_404(note_id, current_user, db)
    try:
        db.delete(note)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to delete note.") from exc
