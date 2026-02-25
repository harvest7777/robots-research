"""seed scenarios

Revision ID: c3f8a1b2d4e9
Revises: a9d623511194
Create Date: 2026-02-25

"""

import json
from collections.abc import Sequence
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision: str = "c3f8a1b2d4e9"
down_revision: str | None = "a9d623511194"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCENARIOS_DIR = Path(__file__).parent.parent.parent.parent / "scenarios"


def _load_scenarios() -> list[dict]:
    rows = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        if path.stem.startswith("_") or path.stem.startswith("example_"):
            continue
        data = json.loads(path.read_text())
        rows.append({"name": path.stem, "data": json.dumps(data)})
    return rows


def upgrade() -> None:
    rows = _load_scenarios()
    if not rows:
        return
    conn = op.get_bind()
    conn.execute(
        text("INSERT INTO scenarios (name, data) VALUES (:name, :data::jsonb)"),
        rows,
    )


def downgrade() -> None:
    rows = _load_scenarios()
    if not rows:
        return
    names = [r["name"] for r in rows]
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM scenarios WHERE name = ANY(:names)"),
        {"names": names},
    )
