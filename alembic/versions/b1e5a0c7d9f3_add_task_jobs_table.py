"""add_task_jobs_table

Revision ID: b1e5a0c7d9f3
Revises: e4f2a1b8c9d7
Create Date: 2025-12-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1e5a0c7d9f3"
down_revision: Union[str, Sequence[str], None] = "e4f2a1b8c9d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "task_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("audio_id", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audio_id"], ["audio_files.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_task_jobs_user_id", "task_jobs", ["user_id"])
    op.create_index("idx_task_jobs_status", "task_jobs", ["status"])
    op.create_index("idx_task_jobs_task_type", "task_jobs", ["task_type"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_task_jobs_task_type")
    op.drop_index("idx_task_jobs_status")
    op.drop_index("idx_task_jobs_user_id")
    op.drop_table("task_jobs")
