from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models import KnowledgePoint, ReviewItem

REVIEW_INTERVALS = [1, 3, 7, 14]


def next_interval(current_interval: int, is_correct: bool) -> int:
    if not is_correct:
        return 1
    for interval in REVIEW_INTERVALS:
        if interval > current_interval:
            return interval
    return REVIEW_INTERVALS[-1]


def schedule_reviews(
    session: Session,
    user_id: str,
    lesson_id: int,
    knowledge_point_ids: list[int],
    is_correct: bool = True,
    now: datetime | None = None,
) -> list[ReviewItem]:
    now = now or datetime.now(UTC)
    updated: list[ReviewItem] = []
    for point_id in knowledge_point_ids:
        item = session.exec(
            select(ReviewItem)
            .where(ReviewItem.user_id == user_id)
            .where(ReviewItem.knowledge_point_id == point_id)
        ).first()
        if item:
            item.interval_days = next_interval(item.interval_days, is_correct)
            item.mistakes = item.mistakes + (0 if is_correct else 1)
            item.due_at = now + timedelta(days=item.interval_days)
            item.updated_at = now
        else:
            interval = REVIEW_INTERVALS[0]
            item = ReviewItem(
                user_id=user_id,
                knowledge_point_id=point_id,
                lesson_id=lesson_id,
                interval_days=interval,
                due_at=now + timedelta(days=interval),
                mistakes=0 if is_correct else 1,
            )
            session.add(item)
        updated.append(item)
    session.commit()
    return updated


def due_reviews(session: Session, user_id: str, now: datetime | None = None) -> list[ReviewItem]:
    now = now or datetime.now(UTC)
    return session.exec(
        select(ReviewItem).where(ReviewItem.user_id == user_id).where(ReviewItem.due_at <= now)
    ).all()


def format_due_reviews(session: Session, user_id: str) -> str:
    items = due_reviews(session, user_id)
    if not items:
        return "今天没有到期复习。可以发送 /today 学习新内容。"
    lines = ["今天需要复习："]
    for item in items:
        point = session.get(KnowledgePoint, item.knowledge_point_id)
        title = point.title if point else f"知识点 {item.knowledge_point_id}"
        lines.append(f"- {title}：间隔 {item.interval_days} 天，累计错 {item.mistakes} 次")
    lines.append("请任选一个知识点，用自己的话解释一下，我会帮你检查。")
    return "\n".join(lines)
