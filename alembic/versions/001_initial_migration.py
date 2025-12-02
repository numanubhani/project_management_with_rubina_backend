"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2025-03-12 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workspaces table first (no dependencies)
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workspaces_code'), 'workspaces', ['code'], unique=True)
    
    # Create users table (depends on workspaces)
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'client', name='userrole'), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create projects table (depends on workspaces and users)
    op.create_table(
        'projects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'delivered', 'completed', name='projectstatus'), nullable=True),
        sa.Column('payment_status', sa.Enum('unpaid', 'pending_approval', 'paid', name='paymentstatus'), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create project_files table (depends on projects and users)
    op.create_table(
        'project_files',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.String(), nullable=False),
        sa.Column('file_category', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('uploaded_by', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create comments table (depends on projects and users)
    op.create_table(
        'comments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create project_updates table (depends on projects)
    op.create_table(
        'project_updates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    # Drop tables in reverse order of dependencies
    op.drop_table('project_updates')
    op.drop_table('comments')
    op.drop_table('project_files')
    op.drop_table('projects')
    op.drop_table('users')
    op.drop_table('workspaces')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS projectstatus')
    op.execute('DROP TYPE IF EXISTS userrole')

