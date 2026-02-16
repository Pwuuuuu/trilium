from __future__ import annotations

from pydantic import BaseModel, Field


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    pinned: bool
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)


class NoteListItem(BaseModel):
    id: int
    title: str
    excerpt: str
    pinned: bool
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)
