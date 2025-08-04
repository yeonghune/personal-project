import uuid
from typing import TYPE_CHECKING
import datetime

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user_models import User


class TodoBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    due_time: datetime.datetime = Field(default=datetime.datetime.now())


class TodoCreate(TodoBase):
    pass


class TodoUpdate(TodoBase):
    pass


class Todo(TodoBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: "User" = Relationship(back_populates="todos")


class TodoPublic(TodoBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class TodosPublic(SQLModel):
    data: list[TodoPublic]
    count: int
