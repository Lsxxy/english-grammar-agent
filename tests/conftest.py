from collections.abc import Generator

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.schemas import LessonIn
from app.services.content import upsert_lesson


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


@pytest.fixture
def sample_lessons(session: Session) -> None:
    upsert_lesson(
        session,
        LessonIn.model_validate(
            {
                "title": "句子成分总览",
                "url": "https://example.com/1",
                "episode_order": 1,
                "notes_markdown": "主语说明谁或什么，谓语说明动作或状态。",
                "key_points": [
                    {"title": "主语", "difficulty": 1, "examples": ["Tom runs."]},
                    {"title": "谓语", "difficulty": 1, "examples": ["She reads."]},
                ],
            }
        ),
    )
    upsert_lesson(
        session,
        LessonIn.model_validate(
            {
                "title": "五大基本句型",
                "url": "https://example.com/2",
                "episode_order": 2,
                "notes_markdown": "五大基本句型包括 SV、SVC、SVO、SVOO、SVOC。",
                "key_points": [{"title": "SVO", "difficulty": 2, "examples": ["I like it."]}],
            }
        ),
    )
