"""add_notifications_table

Revision ID: h4b6d9e2a5c7
Revises: g3a5c8e1f2b4
Create Date: 2025-12-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = "h4b6d9e2a5c7"
down_revision: Union[str, Sequence[str], None] = "g3a5c8e1f2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("data", JSON, nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    
    # Drop table
    op.drop_table("notifications")

