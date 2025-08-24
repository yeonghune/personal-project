import uuid
from typing import Any
import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import Todo, TodoCreate, TodoPublic, TodosPublic, TodoUpdate, Message
from app.services.todo_scheduler import get_scheduler

router = APIRouter(prefix="/todos", tags=["todos"])

@router.get("/", response_model=TodosPublic)
def read_todos(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve todos.
    """

    count_statement = (
        select(func.count())
        .select_from(Todo)
        .where(Todo.owner_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Todo)
        .where(Todo.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    todos = session.exec(statement).all()

    return TodosPublic(data=todos, count=count)

@router.get("/{id}", response_model=TodoPublic)
def read_todo(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    todo = session.get(Todo, id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    return todo

@router.post("/", response_model=TodoPublic)
def create_todo(
    *, session: SessionDep, current_user: CurrentUser, todo_in: TodoCreate
) -> Any:
    """
    Create new todo.
    """
    # Normalize due_time to naive UTC
    due = todo_in.due_time
    if isinstance(due, datetime.datetime):
        if due.tzinfo is not None:
            due = due.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    todo = Todo.model_validate(todo_in, update={"owner_id": current_user.id, "due_time": due})
    session.add(todo)
    session.commit()
    session.refresh(todo)
    # schedule if within window
    try:
        scheduler = get_scheduler()
        scheduler.schedule_if_within_window(todo=todo)
    except Exception:
        pass
    return todo

@router.put("/{id}", response_model=TodoPublic)
def update_todo(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    todo_in: TodoUpdate
) -> Any:
    """
    Update an item.
    """
    todo = session.get(Todo, id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    update_dict = todo_in.model_dump(exclude_unset=True)
    if "due_time" in update_dict and isinstance(update_dict["due_time"], datetime.datetime):
        ud = update_dict["due_time"]
        if ud.tzinfo is not None:
            update_dict["due_time"] = ud.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    todo.sqlmodel_update(update_dict)
    session.add(todo)
    session.commit()
    session.refresh(todo)
    try:
        scheduler = get_scheduler()
        scheduler.reschedule(todo=todo)
    except Exception:
        pass
    return todo

@router.delete("/{id}")
def delete_todo(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an todo.
    """
    todo = session.get(Todo, id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    try:
        scheduler = get_scheduler()
        scheduler.cancel(todo_id=todo.id)
    except Exception:
        pass
    session.delete(todo)
    session.commit()
    return Message(message="Todo deleted successfully")


@router.post("/hydrate", dependencies=[Depends(get_current_active_superuser)])
def hydrate_todo_reminders() -> Message:
    """
    Manually trigger scheduler hydration for the next window (admin only).
    """
    try:
        scheduler = get_scheduler()
        # Run hydration in background; the operation is quick anyway
        import asyncio

        asyncio.create_task(scheduler.hydrate())
    except Exception:
        raise HTTPException(status_code=500, detail="Scheduler not available")
    return Message(message="Hydration triggered")