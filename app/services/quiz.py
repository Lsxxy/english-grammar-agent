from sqlmodel import Session, select

from app.models import Exercise, ExerciseType, KnowledgePoint
from app.schemas import GradeResult


def generate_exercises(session: Session, lesson_id: int) -> list[Exercise]:
    existing = session.exec(select(Exercise).where(Exercise.lesson_id == lesson_id)).all()
    if existing:
        return existing

    points = session.exec(select(KnowledgePoint).where(KnowledgePoint.lesson_id == lesson_id)).all()
    exercises: list[Exercise] = []
    for point in points:
        prompt = f"请写一个包含「{point.title}」这个语法点的英文例句，并标出它在句子中的作用。"
        exercise = Exercise(
            knowledge_point_id=point.id or 0,
            lesson_id=lesson_id,
            type=ExerciseType.SENTENCE,
            prompt=prompt,
            answer="答案不唯一。重点是句子语法正确，并能说明该语法点的作用。",
            explanation=(
                f"检查时重点看：句子是否完整、{point.title} 是否被正确使用、"
                "中文说明是否准确。"
            ),
        )
        session.add(exercise)
        exercises.append(exercise)
    if not exercises:
        exercise = Exercise(
            knowledge_point_id=0,
            lesson_id=lesson_id,
            type=ExerciseType.SENTENCE,
            prompt="请用今天的语法点写一个英文句子，并解释句子结构。",
            answer="答案不唯一。",
            explanation="重点看句子结构说明是否与课程笔记一致。",
        )
        session.add(exercise)
        exercises.append(exercise)
    session.commit()
    return exercises


def format_quiz(exercises: list[Exercise]) -> str:
    lines = ["今日练习："]
    for index, exercise in enumerate(exercises, start=1):
        lines.append(f"{index}. {exercise.prompt}")
    lines.append("直接回复你的答案即可，我会批改并安排复习。")
    return "\n".join(lines)


def grade_answer_locally(answer: str, expected: str | None = None) -> GradeResult:
    normalized = answer.strip()
    if not normalized:
        return GradeResult(is_correct=False, mastery_delta=-0.1, feedback="你还没有写答案。")
    has_english = any("a" <= char.lower() <= "z" for char in normalized)
    has_explanation = any(char in normalized for char in ["主", "谓", "宾", "表", "定", "状", "补"])
    is_correct = has_english and (has_explanation or len(normalized.split()) >= 5)
    if is_correct:
        return GradeResult(
            is_correct=True,
            mastery_delta=0.2,
            feedback="这份答案基本符合要求。下一步可以尝试说明句子主干和修饰成分。",
            correct_answer=expected,
        )
    return GradeResult(
        is_correct=False,
        mastery_delta=-0.1,
        feedback="答案还不够完整。请至少写一个英文句子，并说明相关语法点在句子中的作用。",
        correct_answer=expected,
    )
