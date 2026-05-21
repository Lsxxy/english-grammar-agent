from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session

from app.config import Settings
from app.db import engine
from app.services.agent import GrammarAgent
from app.services.feishu import FeishuClient


def build_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        push_daily_lesson,
        CronTrigger(
            hour=settings.daily_lesson_hour,
            minute=settings.daily_lesson_minute,
            timezone=settings.timezone,
        ),
        args=[settings],
        id="daily-lesson",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    return scheduler


async def push_daily_lesson(settings: Settings) -> None:
    if not settings.feishu_default_receive_id:
        return
    with Session(engine) as session:
        text = await GrammarAgent(settings).today(session, settings.default_user_id)
    await FeishuClient(settings).send_text(settings.feishu_default_receive_id, text)
