from sqlmodel import Session, select

from app.models import Lesson, ReviewItem, StudySession


def format_progress(session: Session, user_id: str) -> str:
    sessions = session.exec(select(StudySession).where(StudySession.user_id == user_id)).all()
    lessons = session.exec(select(Lesson)).all()
    reviews = session.exec(select(ReviewItem).where(ReviewItem.user_id == user_id)).all()
    completed = [item for item in sessions if item.mastery_score >= 0.6]
    avg_mastery = sum(item.mastery_score for item in sessions) / len(sessions) if sessions else 0
    return "\n".join(
        [
            "学习进度：",
            f"- 已开启课程：{len(sessions)} / {len(lessons)}",
            f"- 基本掌握课程：{len(completed)}",
            f"- 平均掌握度：{avg_mastery:.0%}",
            f"- 复习队列：{len(reviews)} 个知识点",
        ]
    )
