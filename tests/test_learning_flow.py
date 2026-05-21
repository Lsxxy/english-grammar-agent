from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from app.config import Settings
from app.models import ReviewItem, StudySession
from app.services.agent import GrammarAgent, looks_like_answer, parse_command
from app.services.content import get_today_lesson
from app.services.review import due_reviews, next_interval, schedule_reviews


def test_today_lesson_follows_learning_order(session: Session, sample_lessons: None) -> None:
    first = get_today_lesson(session, "u1", today=date(2026, 5, 21))
    second = get_today_lesson(session, "u1", today=date(2026, 5, 22))

    assert first is not None
    assert second is not None
    assert first.episode_order == 1
    assert second.episode_order == 2


def test_review_interval_updates_by_answer_quality(session: Session, sample_lessons: None) -> None:
    lesson = get_today_lesson(session, "u1", today=date(2026, 5, 21))
    assert lesson is not None
    schedule_reviews(session, "u1", lesson.id or 0, [1], is_correct=True)
    item = session.exec(select(ReviewItem)).one()

    assert item.interval_days == 1
    assert next_interval(item.interval_days, True) == 3
    assert next_interval(item.interval_days, False) == 1


def test_due_reviews_only_returns_due_items(session: Session, sample_lessons: None) -> None:
    now = datetime(2026, 5, 21, tzinfo=UTC)
    session.add(
        ReviewItem(
            user_id="u1",
            knowledge_point_id=1,
            lesson_id=1,
            due_at=now - timedelta(minutes=1),
        )
    )
    session.add(
        ReviewItem(
            user_id="u1",
            knowledge_point_id=2,
            lesson_id=1,
            due_at=now + timedelta(days=1),
        )
    )
    session.commit()

    assert len(due_reviews(session, "u1", now=now)) == 1


def test_command_and_answer_detection() -> None:
    assert parse_command("/today please") == "/today"
    assert parse_command("什么是主语？") is None
    assert looks_like_answer("Tom is a student. 主语是 Tom")
    assert not looks_like_answer("什么是 SVO？")


async def test_agent_today_and_answer_updates_review_queue(
    session: Session, sample_lessons: None
) -> None:
    agent = GrammarAgent(Settings(openai_api_key=None))
    today_text = await agent.handle_message(session, "u1", "/today")
    answer_text = await agent.handle_message(session, "u1", "Tom is a student. 主语是 Tom")

    assert "今日语法" in today_text
    assert "判断：基本正确" in answer_text
    assert session.exec(select(StudySession)).first() is not None
    assert session.exec(select(ReviewItem)).first() is not None
