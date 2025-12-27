"""add_folders_table

Revision ID: g3a5c8e1f2b4
Revises: f2c4b7d9e8a1
Create Date: 2025-12-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g3a5c8e1f2b4"
down_revision: Union[str, Sequence[str], None] = "f2c4b7d9e8a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create folders table
    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_folders_id", "folders", ["id"], unique=False)
    op.create_index("ix_folders_user_id", "folders", ["user_id"], unique=False)
    
    # Add folder_id to audio_files table
    op.add_column("audio_files", sa.Column("folder_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_audio_files_folder_id",
        "audio_files", "folders",
        ["folder_id"], ["id"],
        ondelete="SET NULL"
    )
    op.create_index("ix_audio_files_folder_id", "audio_files", ["folder_id"], unique=False)


def downgrade() -> None:
    # Remove folder_id from audio_files
    op.drop_index("ix_audio_files_folder_id", table_name="audio_files")
    op.drop_constraint("fk_audio_files_folder_id", "audio_files", type_="foreignkey")
    op.drop_column("audio_files", "folder_id")
    
    # Drop folders table
    op.drop_index("ix_folders_user_id", table_name="folders")
    op.drop_index("ix_folders_id", table_name="folders")
    op.drop_table("folders")

