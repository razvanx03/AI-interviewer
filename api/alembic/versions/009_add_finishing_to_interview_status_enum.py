"""add finishing to interview_status_enum

Revision ID: 009_add_finishing_status
Revises: 008_create_users_table
Create Date: 2026-08-30 13:37:00.000000
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '009_add_finishing_status'
down_revision: Union[str, None] = '008_create_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("ALTER TYPE interview_status_enum ADD VALUE IF NOT EXISTS 'finishing'")

def downgrade() -> None:
    pass
