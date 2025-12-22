"""add_note_chunks_and_remove_embeddings

Revision ID: e4f2a1b8c9d7
Revises: 64837bfe8eef
Create Date: 2025-12-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'e4f2a1b8c9d7'
down_revision: Union[str, Sequence[str], None] = '64837bfe8eef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create note_chunks table and remove embedding columns from notes."""
    
    # Create note_chunks table
    op.create_table(
        'note_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('note_id', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_type', sa.String(length=20), nullable=False, server_default='content'),
        sa.Column('embedding', Vector(768), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['note_id'], ['notes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index(op.f('ix_note_chunks_id'), 'note_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_note_chunks_note_id'), 'note_chunks', ['note_id'], unique=False)
    
    # Remove embedding columns from notes table
    op.drop_column('notes', 'content_embedding')
    op.drop_column('notes', 'summary_embedding')


def downgrade() -> None:
    """Downgrade schema: Add back embedding columns to notes and drop note_chunks table."""
    
    # Add back embedding columns to notes
    op.add_column('notes', sa.Column('summary_embedding', Vector(768), nullable=True))
    op.add_column('notes', sa.Column('content_embedding', Vector(768), nullable=True))
    
    # Drop note_chunks table
    op.drop_index(op.f('ix_note_chunks_note_id'), table_name='note_chunks')
    op.drop_index(op.f('ix_note_chunks_id'), table_name='note_chunks')
    op.drop_table('note_chunks')
