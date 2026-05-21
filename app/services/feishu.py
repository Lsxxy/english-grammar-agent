import json
import time
from dataclasses import dataclass

import httpx

from app.config import Settings


@dataclass(frozen=True)
class IncomingFeishuMessage:
    event_id: str
    user_id: str
    text: str
    message_id: str | None = None


class FeishuClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._tenant_access_token: str | None = None
        self._token_expires_at = 0.0

    async def send_text(self, receive_id: str, text: str) -> None:
        if not self.settings.feishu_app_id or not self.settings.feishu_app_secret:
            return
        token = await self._tenant_token()
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        params = {"receive_id_type": self.settings.feishu_receive_id_type}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/im/v1/messages",
                params=params,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()

    async def _tenant_token(self) -> str:
        if self._tenant_access_token and time.time() < self._token_expires_at - 60:
            return self._tenant_access_token
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.settings.feishu_app_id,
                    "app_secret": self.settings.feishu_app_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
        token = data.get("tenant_access_token")
        if not token:
            raise RuntimeError(f"Feishu tenant token missing: {data}")
        self._tenant_access_token = token
        self._token_expires_at = time.time() + int(data.get("expire", 7200))
        return token


def parse_feishu_event(payload: dict, settings: Settings) -> IncomingFeishuMessage | None:
    if payload.get("type") == "url_verification":
        return None
    if settings.feishu_verification_token:
        token = payload.get("token") or payload.get("header", {}).get("token")
        if token and token != settings.feishu_verification_token:
            raise ValueError("Invalid Feishu verification token")

    header = payload.get("header", {})
    event = payload.get("event", {})
    event_type = header.get("event_type") or event.get("type")
    if event_type not in {"im.message.receive_v1", "message"}:
        return None

    message = event.get("message", {})
    sender = event.get("sender", {})
    text = _extract_text(message)
    user_id = (
        sender.get("sender_id", {}).get("open_id")
        or sender.get("sender_id", {}).get("user_id")
        or event.get("open_id")
        or "local-user"
    )
    event_id = header.get("event_id") or payload.get("uuid") or message.get("message_id")
    return IncomingFeishuMessage(
        event_id=event_id or f"event-{time.time_ns()}",
        user_id=user_id,
        text=text,
        message_id=message.get("message_id"),
    )


def challenge_response(payload: dict) -> dict | None:
    if payload.get("type") == "url_verification" and payload.get("challenge"):
        return {"challenge": payload["challenge"]}
    if payload.get("challenge"):
        return {"challenge": payload["challenge"]}
    return None


def _extract_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError:
            return content
        if isinstance(decoded, dict):
            return str(decoded.get("text") or decoded.get("content") or "").strip()
    if isinstance(content, dict):
        return str(content.get("text") or "").strip()
    return ""
