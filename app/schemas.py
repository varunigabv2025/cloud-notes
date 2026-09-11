from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class SignupInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("confirm_password")
    @classmethod
    def passwords_must_match(cls, value: str, info) -> str:
        if value != info.data.get("password"):
            raise ValueError("Passwords do not match.")
        return value


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime
