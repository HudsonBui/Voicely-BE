"""add_chatbot_tables

Revision ID: d4a2c0b4c3f1
Revises: b1e5a0c7d9f3
Create Date: 2025-12-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4a2c0b4c3f1"
down_revision: Union[str, Sequence[str], None] = "b1e5a0c7d9f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "chatbot_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("total_messages", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("idx_chatbot_session_user_id", "chatbot_sessions", ["user_id"])
    op.create_index("idx_chatbot_session_active", "chatbot_sessions", ["is_active"])
    op.create_index("idx_chatbot_session_session_id", "chatbot_sessions", ["session_id"])

    op.create_table(
        "chatbot_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("entities", postgresql.JSONB(), nullable=True),
        sa.Column("retrieved_chunks", postgresql.JSONB(), nullable=True),
        sa.Column("retrieved_audio_ids", postgresql.JSONB(), nullable=True),
        sa.Column("retrieved_note_ids", postgresql.JSONB(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chatbot_sessions.session_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index("idx_chatbot_message_session", "chatbot_messages", ["session_id"])
    op.create_index("idx_chatbot_message_created", "chatbot_messages", ["created_at"])
    op.create_index("idx_chatbot_message_message_id", "chatbot_messages", ["message_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_chatbot_message_message_id", table_name="chatbot_messages")
    op.drop_index("idx_chatbot_message_created", table_name="chatbot_messages")
    op.drop_index("idx_chatbot_message_session", table_name="chatbot_messages")
    op.drop_table("chatbot_messages")
    op.drop_index("idx_chatbot_session_session_id", table_name="chatbot_sessions")
    op.drop_index("idx_chatbot_session_active", table_name="chatbot_sessions")
    op.drop_index("idx_chatbot_session_user_id", table_name="chatbot_sessions")
    op.drop_table("chatbot_sessions")
