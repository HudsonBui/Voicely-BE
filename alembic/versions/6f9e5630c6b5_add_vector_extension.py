"""add_vector_extension

Revision ID: 6f9e5630c6b5
Revises: c79124a8796a
Create Date: 2025-11-23 14:53:26.658838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f9e5630c6b5'
down_revision: Union[str, Sequence[str], None] = 'c79124a8796a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kích hoạt extension vector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
