import json
from datetime import date

from sqlmodel import Session, asc, select

from app.models import KnowledgePoint, Lesson, LessonStatus, StudySession
from app.schemas import KnowledgePointIn, LessonIn, LessonOut


def upsert_lesson(session: Session, payload: LessonIn) -> Lesson:
    existing = session.exec(
        select(Lesson).where(Lesson.episode_order == payload.episode_order)
    ).first()
    if existing:
        existing.title = payload.title
        existing.url = payload.url
        existing.notes_markdown = payload.notes_markdown
        existing.status = LessonStatus.READY
        lesson = existing
    else:
        lesson = Lesson(
            title=payload.title,
            url=payload.url,
            episode_order=payload.episode_order,
            notes_markdown=payload.notes_markdown,
        )
        session.add(lesson)
    session.commit()
    session.refresh(lesson)

    old_points = session.exec(
        select(KnowledgePoint).where(KnowledgePoint.lesson_id == lesson.id)
    ).all()
    for point in old_points:
        session.delete(point)
    for point in payload.key_points:
        session.add(
            KnowledgePoint(
                lesson_id=lesson.id,
                title=point.title,
                difficulty=point.difficulty,
                examples_json=json.dumps(point.examples, ensure_ascii=False),
            )
        )
    session.commit()
    session.refresh(lesson)
    return lesson


def list_lesson_outputs(session: Session) -> list[LessonOut]:
    lessons = session.exec(select(Lesson).order_by(asc(Lesson.episode_order))).all()
    return [lesson_to_output(session, lesson) for lesson in lessons]


def lesson_to_output(session: Session, lesson: Lesson) -> LessonOut:
    points = session.exec(
        select(KnowledgePoint).where(KnowledgePoint.lesson_id == lesson.id)
    ).all()
    return LessonOut(
        id=lesson.id or 0,
        title=lesson.title,
        url=lesson.url,
        episode_order=lesson.episode_order,
        notes_markdown=lesson.notes_markdown,
        key_points=[
            KnowledgePointIn(
                title=point.title,
                difficulty=point.difficulty,
                examples=json.loads(point.examples_json or "[]"),
            )
            for point in points
        ],
    )


def get_today_lesson(session: Session, user_id: str, today: date | None = None) -> Lesson | None:
    today = today or date.today()
    existing_session = session.exec(
        select(StudySession)
        .where(StudySession.user_id == user_id)
        .where(StudySession.session_date == today)
    ).first()
    if existing_session:
        return session.get(Lesson, existing_session.lesson_id)

    completed_count = len(
        session.exec(select(StudySession).where(StudySession.user_id == user_id)).all()
    )
    lessons = session.exec(
        select(Lesson)
        .where(Lesson.status == LessonStatus.READY)
        .order_by(asc(Lesson.episode_order))
    ).all()
    if not lessons:
        return None
    lesson = lessons[completed_count % len(lessons)]
    session.add(StudySession(user_id=user_id, lesson_id=lesson.id or 0, session_date=today))
    session.commit()
    return lesson


def get_lesson_points(session: Session, lesson_id: int) -> list[KnowledgePoint]:
    return session.exec(select(KnowledgePoint).where(KnowledgePoint.lesson_id == lesson_id)).all()
