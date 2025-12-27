"""add_user_devices_table

Revision ID: f2c4b7d9e8a1
Revises: d4a2c0b4c3f1
Create Date: 2025-12-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c4b7d9e8a1"
down_revision: Union[str, Sequence[str], None] = "d4a2c0b4c3f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fcm_token", sa.String(), nullable=False),
        sa.Column("device_type", sa.String(), nullable=True),
        sa.Column("device_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fcm_token"),
    )
    op.create_index("ix_user_devices_user_id", "user_devices", ["user_id"])
    op.create_index("ix_user_devices_fcm_token", "user_devices", ["fcm_token"])


def downgrade() -> None:
    op.drop_index("ix_user_devices_fcm_token", table_name="user_devices")
    op.drop_index("ix_user_devices_user_id", table_name="user_devices")
    op.drop_table("user_devices")
