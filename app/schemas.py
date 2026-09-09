from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteInput(BaseModel):
    title: str = Field(..., max_length=200, description="A short title for the note")
    content: str = Field(default="", max_length=10000)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        return value


class NoteResponse(NoteInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
