import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlmodel import Session, select

from app.core.db import engine
from app.models import Todo, User
from app.utils import EmailData, send_email, generate_todo_due_email


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _seconds_until(dt_utc_naive: datetime) -> float:
    now = _utcnow_naive()
    return max(0.0, (dt_utc_naive - now).total_seconds())


def _build_todo_email(*, owner_email: str, title: str, description: str | None, due_time: datetime) -> EmailData:
    subject = f"[Todo Reminder] {title}"
    safe_desc = description or "(no description)"
    # Simple inline HTML; reuse send_email transport
    html = (
        f"<h3>Todo Reminder</h3>"
        f"<p><b>Title:</b> {title}</p>"
        f"<p><b>Description:</b> {safe_desc}</p>"
        f"<p><b>Due (UTC):</b> {due_time.strftime('%Y-%m-%d %H:%M:%S')}</p>"
    )
    return EmailData(html_content=html, subject=subject)


class TodoScheduler:
    def __init__(self, *, window_minutes: int = 5, hydrate_interval_seconds: int = 60, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self.window_minutes = window_minutes
        self.hydrate_interval_seconds = hydrate_interval_seconds
        self._jobs: dict[uuid.UUID, Any] = {}
        self._hydrator_task: asyncio.Task[Any] | None = None
        # Main event loop where tasks should run
        self._loop: asyncio.AbstractEventLoop | None = loop

    async def hydrate(self) -> None:
        now = _utcnow_naive()
        upper = now + timedelta(minutes=self.window_minutes)
        with Session(engine) as session:
            statement = select(Todo).where(Todo.due_time > now, Todo.due_time <= upper)
            todos = session.exec(statement).all()
            for todo in todos:
                if isinstance(todo.id, uuid.UUID) and todo.id not in self._jobs:
                    self._schedule_task(session=session, todo=todo)

    def start_background_hydrator(self) -> None:
        async def _loop() -> None:
            while True:
                try:
                    await self.hydrate()
                except Exception:
                    # Best-effort loop; errors shouldn't kill loop
                    pass
                await asyncio.sleep(self.hydrate_interval_seconds)

        if self._hydrator_task is None or self._hydrator_task.done():
            assert self._loop is not None, "Scheduler loop not set"
            self._hydrator_task = self._loop.create_task(_loop())

    async def shutdown(self) -> None:
        for task in list(self._jobs.values()):
            task.cancel()
        self._jobs.clear()
        if self._hydrator_task is not None:
            self._hydrator_task.cancel()
            self._hydrator_task = None

    def schedule_if_within_window(self, *, todo: Todo) -> None:
        now = _utcnow_naive()
        if todo.due_time <= now:
            return
        if (todo.due_time - now) > timedelta(minutes=self.window_minutes):
            return
        with Session(engine) as session:
            self._schedule_task(session=session, todo=todo)

    def reschedule(self, *, todo: Todo) -> None:
        self.cancel(todo_id=todo.id)
        self.schedule_if_within_window(todo=todo)

    def cancel(self, *, todo_id: uuid.UUID) -> None:
        task = self._jobs.pop(todo_id, None)
        if task is not None:
            task.cancel()

    def _schedule_task(self, *, session: Session, todo: Todo) -> None:
        if todo.id in self._jobs:
            return

        delay = _seconds_until(todo.due_time)

        async def _runner(todo_id: uuid.UUID) -> None:
            try:
                await asyncio.sleep(delay)
                with Session(engine) as inner:
                    db_todo = inner.get(Todo, todo_id)
                    if not db_todo:
                        return
                    owner = inner.get(User, db_todo.owner_id)
                    if not owner or not getattr(owner, "email", None):
                        return
                    email = generate_todo_due_email(
                        email_to=owner.email,
                        title=db_todo.title,
                        description=db_todo.description,
                        due_time_utc=db_todo.due_time,
                    )
                    send_email(email_to=owner.email, subject=email.subject, html_content=email.html_content)
            finally:
                # Remove from registry regardless of outcome
                self._jobs.pop(todo.id, None)

        # Ensure task is scheduled on the main event loop
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop in this thread; leave as None (will fail below)
                pass
        assert self._loop is not None, "Scheduler loop not set"
        try:
            running_loop = asyncio.get_running_loop()
            if running_loop is self._loop:
                self._jobs[todo.id] = self._loop.create_task(_runner(todo.id))
            else:
                fut = asyncio.run_coroutine_threadsafe(_runner(todo.id), self._loop)
                self._jobs[todo.id] = fut
        except RuntimeError:
            # Called from a worker thread without a running loop
            fut = asyncio.run_coroutine_threadsafe(_runner(todo.id), self._loop)
            self._jobs[todo.id] = fut


# Global accessors
SCHEDULER: TodoScheduler | None = None


def init_scheduler(*, window_minutes: int = 5, hydrate_interval_seconds: int = 60, loop: asyncio.AbstractEventLoop | None = None) -> TodoScheduler:
    global SCHEDULER
    if loop is None:
        loop = asyncio.get_running_loop()
    SCHEDULER = TodoScheduler(window_minutes=window_minutes, hydrate_interval_seconds=hydrate_interval_seconds, loop=loop)
    return SCHEDULER


def get_scheduler() -> TodoScheduler:
    assert SCHEDULER is not None, "Scheduler not initialized"
    return SCHEDULER


