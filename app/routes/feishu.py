from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db import get_session
from app.models import FeishuEventLog
from app.services.agent import GrammarAgent
from app.services.feishu import FeishuClient, challenge_response, parse_feishu_event

router = APIRouter(prefix="/feishu", tags=["feishu"])
SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("/events")
async def feishu_events(
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    settings: SettingsDep,
) -> dict[str, str]:
    payload = await request.json()
    challenge = challenge_response(payload)
    if challenge:
        return challenge

    try:
        incoming = parse_feishu_event(payload, settings)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if incoming is None:
        return {"status": "ignored"}
    existing = session.exec(
        select(FeishuEventLog).where(FeishuEventLog.event_id == incoming.event_id)
    ).first()
    if existing:
        return {"status": "duplicate"}
    session.add(FeishuEventLog(event_id=incoming.event_id))
    session.commit()

    background_tasks.add_task(_process_message, incoming.user_id, incoming.text, settings)
    return {"status": "accepted"}


async def _process_message(user_id: str, text: str, settings: Settings) -> None:
    from sqlmodel import Session

    from app.db import engine

    with Session(engine) as session:
        reply = await GrammarAgent(settings).handle_message(session, user_id, text)
    await FeishuClient(settings).send_text(user_id, reply)
