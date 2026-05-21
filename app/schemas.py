from pydantic import BaseModel, Field


class KnowledgePointIn(BaseModel):
    title: str
    difficulty: int = Field(default=1, ge=1, le=5)
    examples: list[str] = Field(default_factory=list)


class LessonIn(BaseModel):
    title: str
    url: str | None = None
    episode_order: int
    notes_markdown: str
    key_points: list[KnowledgePointIn] = Field(default_factory=list)


class LessonOut(BaseModel):
    id: int
    title: str
    url: str | None
    episode_order: int
    notes_markdown: str
    key_points: list[KnowledgePointIn]


class GradeResult(BaseModel):
    is_correct: bool
    mastery_delta: float = Field(ge=-1, le=1)
    feedback: str
    correct_answer: str | None = None
