# English Grammar Agent

一个面向通勤学习的英语语法学习 agent：每天通过飞书机器人推送一节课程，支持追问、练习、批改和遗忘曲线复习。

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

初始化示例课程：

```bash
python scripts/import_lessons.py examples/lessons.sample.json
```

本地接口：

- `GET /health`
- `POST /admin/lessons`
- `POST /admin/push-today`
- `POST /feishu/events`

## Feishu Setup

第一版使用飞书自建应用机器人：

1. 在飞书开放平台创建企业自建应用。
2. 开启机器人能力。
3. 配置事件订阅，订阅接收消息事件。
4. 将事件回调地址指向 `https://你的域名/feishu/events`。
5. 在 `.env` 配置 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_VERIFICATION_TOKEN`。
6. 设置 `FEISHU_DEFAULT_RECEIVE_ID` 后可用 `/admin/push-today` 或定时任务主动推送。

## Commands

- `/today`：今日课程
- `/review`：今日复习
- `/quiz`：当前课程练习
- `/progress`：学习进度
- 普通文本：追问或答题

## Model Provider

默认使用 OpenAI Responses API：

```dotenv
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4.1-mini
```

也可以使用 DeepSeek 官方 API：

```dotenv
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

`LLM_BASE_URL` 非空时，项目会改用 OpenAI-compatible Chat Completions 调用。

## Learning Architecture

1. Prompt layer：课程讲解、追问、批改提示词。
2. Tool layer：读取课程、生成习题、批改答案、安排复习。
3. Memory layer：学习记录、聊天记录、复习队列。
4. Delivery layer：飞书事件接入和主动推送。
5. Ops layer：定时任务、日志、测试和部署。
