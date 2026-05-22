from datetime import UTC, date, datetime
from enum import Enum

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class LessonStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class ExerciseType(str, Enum):
    CHOICE = "choice"
    CORRECTION = "correction"
    SENTENCE = "sentence"


class SessionStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Lesson(SQLModel, table=True):
    __tablename__ = "lessons"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    url: str | None = None
    episode_order: int = Field(index=True, unique=True)
    notes_markdown: str = Field(sa_column=Column(Text))
    status: LessonStatus = Field(default=LessonStatus.READY, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class KnowledgePoint(SQLModel, table=True):
    __tablename__ = "knowledge_points"

    id: int | None = Field(default=None, primary_key=True)
    lesson_id: int = Field(foreign_key="lessons.id", index=True)
    title: str
    difficulty: int = Field(default=1, ge=1, le=5)
    examples_json: str = Field(default="[]", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utc_now)


class Exercise(SQLModel, table=True):
    __tablename__ = "exercises"

    id: int | None = Field(default=None, primary_key=True)
    knowledge_point_id: int = Field(foreign_key="knowledge_points.id", index=True)
    lesson_id: int = Field(foreign_key="lessons.id", index=True)
    type: ExerciseType = Field(default=ExerciseType.SENTENCE)
    prompt: str = Field(sa_column=Column(Text))
    answer: str = Field(sa_column=Column(Text))
    explanation: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utc_now)


class StudySession(SQLModel, table=True):
    __tablename__ = "study_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    lesson_id: int = Field(foreign_key="lessons.id", index=True)
    session_date: date = Field(index=True)
    status: SessionStatus = Field(default=SessionStatus.STARTED)
    mastery_score: float = Field(default=0.0, ge=0, le=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewItem(SQLModel, table=True):
    __tablename__ = "review_items"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    knowledge_point_id: int = Field(foreign_key="knowledge_points.id", index=True)
    lesson_id: int = Field(foreign_key="lessons.id", index=True)
    due_at: datetime = Field(index=True)
    interval_days: int = Field(default=1)
    mistakes: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    role: ChatRole
    content: str = Field(sa_column=Column(Text))
    lesson_id: int | None = Field(default=None, foreign_key="lessons.id", index=True)
    study_session_id: int | None = Field(default=None, foreign_key="study_sessions.id", index=True)
    feishu_message_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class FeishuEventLog(SQLModel, table=True):
    __tablename__ = "feishu_event_logs"

    event_id: str = Field(primary_key=True)
    received_at: datetime = Field(default_factory=utc_now)
