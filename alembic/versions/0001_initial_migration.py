"""initial migration - nodes, tasks, users tables

Revision ID: 0001
Revises: 
Create Date: 2026-04-23 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('balance_usd', sa.Float(), nullable=True),
        sa.Column('total_spent_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    
    op.create_table('nodes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('gpu_model', sa.String(length=255), nullable=True),
        sa.Column('gpu_count', sa.Integer(), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('memory_gb', sa.Integer(), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('gpu_utilization', sa.Float(), nullable=True),
        sa.Column('memory_utilization', sa.Float(), nullable=True),
        sa.Column('network_latency_ms', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=9), nullable=True),
        sa.Column('node_id', sa.String(), nullable=True),
        sa.Column('framework', sa.String(length=50), nullable=True),
        sa.Column('gpu_required', sa.Integer(), nullable=True),
        sa.Column('duration_hours', sa.Integer(), nullable=True),
        sa.Column('memory_required_gb', sa.Integer(), nullable=True),
        sa.Column('code_url', sa.Text(), nullable=True),
        sa.Column('data_url', sa.Text(), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('result_path', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('gpu_hours_consumed', sa.Float(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'])
    )


def downgrade() -> None:
    op.drop_table('tasks')
    op.drop_table('nodes')
    op.drop_table('users')
