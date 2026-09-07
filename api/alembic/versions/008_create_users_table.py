"""create users table and seed initial admin account

Revision ID: 008_create_users_table
Revises: 007_add_time_limit_minutes
Create Date: 2026-08-29 15:15:00.000000
"""
from typing import Sequence, Union
import os
import uuid
import datetime
from alembic import op
import sqlalchemy as sa
import bcrypt

# revision identifiers, used by Alembic.
revision: str = '008_create_users_table'
down_revision: Union[str, None] = '007_add_time_limit_minutes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    users_table = op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), server_default='admin', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Seed initial admin user if env vars are present during migration;
    # otherwise startup lifespan (ensure_initial_admin) handles mandatory seeding with fast-fail validation.
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        now = datetime.datetime.now(datetime.timezone.utc)
        salt = bcrypt.gensalt()
        admin_pw_hash = bcrypt.hashpw(admin_password.encode("utf-8"), salt).decode('utf-8')

        op.bulk_insert(
            users_table,
            [
                {
                    'id': str(uuid.uuid4()),
                    'email': admin_email,
                    'hashed_password': admin_pw_hash,
                    'full_name': 'Lead Recruiter Admin',
                    'role': 'admin',
                    'is_active': True,
                    'created_at': now,
                    'updated_at': now,
                }
            ]
        )

def downgrade() -> None:
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
