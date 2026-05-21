from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.schemas import LessonIn, LessonOut
from app.services.agent import GrammarAgent
from app.services.content import lesson_to_output, list_lesson_outputs, upsert_lesson
from app.services.feishu import FeishuClient

router = APIRouter(prefix="/admin", tags=["admin"])
SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/lessons", response_model=list[LessonOut])
def lessons(session: SessionDep) -> list[LessonOut]:
    return list_lesson_outputs(session)


@router.post("/lessons", response_model=LessonOut)
def create_lesson(payload: LessonIn, session: SessionDep) -> LessonOut:
    lesson = upsert_lesson(session, payload)
    return lesson_to_output(session, lesson)


@router.post("/push-today")
async def push_today(
    session: SessionDep,
    settings: SettingsDep,
) -> dict[str, str]:
    if not settings.feishu_default_receive_id:
        raise HTTPException(status_code=400, detail="FEISHU_DEFAULT_RECEIVE_ID is not configured")
    agent = GrammarAgent(settings)
    text = await agent.today(session, settings.default_user_id)
    await FeishuClient(settings).send_text(settings.feishu_default_receive_id, text)
    return {"status": "sent"}
