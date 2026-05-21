import json
import sys
from pathlib import Path

from sqlmodel import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import engine, init_db  # noqa: E402
from app.schemas import LessonIn  # noqa: E402
from app.services.content import upsert_lesson  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/import_lessons.py path/to/lessons.json")
    init_db()
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    with Session(engine) as session:
        for item in payload:
            upsert_lesson(session, LessonIn.model_validate(item))
    print(f"Imported {len(payload)} lessons")


if __name__ == "__main__":
    main()
