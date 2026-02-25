"""create initial schema

Revision ID: a9d623511194
Revises:
Create Date: 2026-02-25

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a9d623511194"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE scenarios (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        TEXT NOT NULL,
            data        JSONB NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE simulation_run_results (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            scenario_id   UUID NOT NULL REFERENCES scenarios(id),
            assignments   JSONB NOT NULL,
            completed     BOOL NOT NULL,
            tasks_done    INT NOT NULL,
            tasks_total   INT NOT NULL,
            makespan      INT,
            max_steps     INT NOT NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE simulation_snapshots (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            simulation_id   UUID NOT NULL REFERENCES simulation_run_results(id),
            step            INT NOT NULL,
            data            JSONB NOT NULL
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE simulation_snapshots")
    op.execute("DROP TABLE simulation_run_results")
    op.execute("DROP TABLE scenarios")
