from datetime import UTC, date, datetime

from sqlmodel import Session, desc, select

from app.config import Settings
from app.models import ChatMessage, ChatRole, KnowledgePoint, Lesson, StudySession
from app.schemas import GradeResult
from app.services.content import get_lesson_points, get_today_lesson
from app.services.llm import LLMClient
from app.services.progress import format_progress
from app.services.quiz import format_quiz, generate_exercises, grade_answer_locally
from app.services.review import format_due_reviews, schedule_reviews


class GrammarAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    async def handle_message(self, session: Session, user_id: str, text: str) -> str:
        command = parse_command(text)
        if command == "/today":
            reply = await self.today(session, user_id)
        elif command == "/review":
            reply = format_due_reviews(session, user_id)
        elif command == "/quiz":
            reply = self.quiz(session, user_id)
        elif command == "/progress":
            reply = format_progress(session, user_id)
        else:
            reply = await self.answer_or_grade(session, user_id, text)
        self._save_chat(session, user_id, ChatRole.USER, text)
        self._save_chat(session, user_id, ChatRole.ASSISTANT, reply)
        session.commit()
        return reply

    async def today(self, session: Session, user_id: str, today: date | None = None) -> str:
        lesson = get_today_lesson(session, user_id, today=today)
        if not lesson:
            return "还没有可学习的课程。请先通过管理接口或导入脚本添加课程笔记。"
        points = get_lesson_points(session, lesson.id or 0)
        exercises = generate_exercises(session, lesson.id or 0)
        point_titles = "、".join(point.title for point in points) or "课程笔记中的核心语法点"
        review_text = format_due_reviews(session, user_id)
        return "\n\n".join(
            [
                f"今日语法：{lesson.title}",
                f"视频链接：{lesson.url}" if lesson.url else "视频链接：未填写",
                f"核心知识点：{point_titles}",
                self._compact_lesson_explanation(lesson, points),
                format_quiz(exercises[:4]),
                review_text,
            ]
        )

    def quiz(self, session: Session, user_id: str) -> str:
        active = self._active_session(session, user_id)
        if not active:
            return "还没有今日课程。发送 /today 开始学习。"
        return format_quiz(generate_exercises(session, active.lesson_id)[:4])

    async def answer_or_grade(self, session: Session, user_id: str, text: str) -> str:
        active = self._active_session(session, user_id)
        if not active:
            return await self._answer_question(session, user_id, text, None, [])

        lesson = session.get(Lesson, active.lesson_id)
        points = get_lesson_points(session, active.lesson_id)
        if looks_like_answer(text):
            result = await self._grade_answer(session, text)
            active.mastery_score = clamp(active.mastery_score + result.mastery_delta, 0, 1)
            active.updated_at = datetime.now(UTC)
            schedule_reviews(
                session,
                user_id=user_id,
                lesson_id=active.lesson_id,
                knowledge_point_ids=[point.id for point in points if point.id],
                is_correct=result.is_correct,
            )
            return format_grade_result(result)
        return await self._answer_question(session, user_id, text, lesson, points)

    async def _grade_answer(self, session: Session, text: str) -> GradeResult:
        active_exercise = session.exec(
            select(ChatMessage).order_by(desc(ChatMessage.created_at))
        ).first()
        expected = active_exercise.content if active_exercise else None
        if not self.settings.active_llm_api_key:
            return grade_answer_locally(text, expected)

        try:
            feedback = await self.llm.complete(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是英语语法学习教练。批改用户答案，输出简洁中文反馈。"
                            "先判断是否基本正确，再指出一个最重要的问题。"
                        ),
                    },
                    {"role": "user", "content": text},
                ],
            )
            if not feedback:
                return grade_answer_locally(text, expected)
            is_correct = "不正确" not in feedback and "错误" not in feedback[:30]
            return GradeResult(
                is_correct=is_correct,
                mastery_delta=0.2 if is_correct else -0.1,
                feedback=feedback,
            )
        except Exception:
            return grade_answer_locally(text, expected)

    async def _answer_question(
        self,
        session: Session,
        user_id: str,
        question: str,
        lesson: Lesson | None,
        points: list[KnowledgePoint],
    ) -> str:
        if not self.settings.active_llm_api_key:
            context = self._local_context(lesson, points)
            return (
                f"我会结合当前课程回答。\n\n{context}\n\n你的问题是：{question}"
                "\n\n建议先回到例句，找出主干，再看修饰成分。"
            )

        recent = session.exec(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(8)
        ).all()
        context = self._local_context(lesson, points)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个通勤场景英语语法学习 agent。回答要短、清楚、适合手机阅读。"
                    "优先依据当前课程内容，不确定时提示用户补充课程笔记。"
                ),
            },
            {"role": "user", "content": f"当前课程上下文：\n{context}"},
        ]
        for message in reversed(recent):
            messages.append({"role": message.role.value, "content": message.content})
        messages.append({"role": "user", "content": question})
        try:
            answer = await self.llm.complete(messages)
            if answer:
                return answer
            return f"当前未配置 AI，我先基于课程笔记回答：\n\n{self._local_context(lesson, points)}"
        except Exception:
            context = self._local_context(lesson, points)
            return f"当前 AI 调用失败，我先基于课程笔记回答：\n\n{context}"

    def _compact_lesson_explanation(self, lesson: Lesson, points: list[KnowledgePoint]) -> str:
        examples = []
        for point in points:
            examples.append(f"- {point.title}：难度 {point.difficulty}/5")
        point_text = "\n".join(examples) if examples else "- 暂无拆分知识点"
        return f"讲解：\n{lesson.notes_markdown[:700]}\n\n知识点拆分：\n{point_text}"

    def _local_context(self, lesson: Lesson | None, points: list[KnowledgePoint]) -> str:
        if not lesson:
            return "当前没有激活课程。发送 /today 可以开始今天的学习。"
        point_titles = "、".join(point.title for point in points) or "未拆分"
        return f"课程：{lesson.title}\n知识点：{point_titles}\n笔记：{lesson.notes_markdown[:800]}"

    def _active_session(self, session: Session, user_id: str) -> StudySession | None:
        return session.exec(
            select(StudySession)
            .where(StudySession.user_id == user_id)
            .order_by(desc(StudySession.session_date), desc(StudySession.created_at))
        ).first()

    def _save_chat(
        self,
        session: Session,
        user_id: str,
        role: ChatRole,
        content: str,
        feishu_message_id: str | None = None,
    ) -> None:
        active = self._active_session(session, user_id)
        session.add(
            ChatMessage(
                user_id=user_id,
                role=role,
                content=content,
                lesson_id=active.lesson_id if active else None,
                study_session_id=active.id if active else None,
                feishu_message_id=feishu_message_id,
            )
        )


def parse_command(text: str) -> str | None:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    return stripped.split(maxsplit=1)[0].lower()


def looks_like_answer(text: str) -> bool:
    stripped = text.strip()
    if "?" in stripped or "？" in stripped:
        return False
    return any("a" <= char.lower() <= "z" for char in stripped) and len(stripped) >= 8


def format_grade_result(result: GradeResult) -> str:
    status = "判断：基本正确" if result.is_correct else "判断：需要修改"
    answer = f"\n参考答案：{result.correct_answer}" if result.correct_answer else ""
    return f"{status}\n{result.feedback}{answer}\n\n我已经根据这次表现更新了复习队列。"


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
