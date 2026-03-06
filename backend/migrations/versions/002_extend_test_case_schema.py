"""Extend test case schema with comprehensive fields

Revision ID: 002_extend_test_case_schema
Revises: 001_initial_schema
Create Date: 2026-03-02 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_extend_test_case_schema"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Extend test_cases table and create related tables"""
    
    # Drop existing test_cases table and recreate with new schema
    op.drop_table('test_cases')
    
    # Create updated test_cases table with all required fields
    op.create_table(
        'test_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('test_case_id', sa.String(50), nullable=False, unique=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('module', sa.String(255), nullable=True),
        sa.Column('priority', sa.Enum('Critical', 'High', 'Medium', 'Low', name='priorityenum'), default='Medium'),
        sa.Column('severity', sa.Enum('Blocker', 'Critical', 'Major', 'Minor', 'Trivial', name='severityenum'), default='Major'),
        sa.Column('type', sa.Enum('Functional', 'Regression', 'Smoke', 'Performance', 'Security', 'Usability', 'Accessibility', 'Integration', name='testtypeenum'), default='Functional'),
        sa.Column('status', sa.Enum('Draft', 'Ready for Review', 'Approved', 'Deprecated', 'Archived', name='testcasestatusenum'), default='Draft'),
        sa.Column('pre_conditions', sa.Text(), nullable=True),
        sa.Column('test_data_requirements', sa.Text(), nullable=True),
        sa.Column('environment_requirements', sa.String(255), nullable=True),
        sa.Column('post_conditions', sa.Text(), nullable=True),
        sa.Column('cleanup_steps', sa.Text(), nullable=True),
        sa.Column('estimated_duration', sa.Integer(), nullable=True),
        sa.Column('automation_status', sa.Enum('Not Automated', 'Automated', 'Partially Automated', 'Deprecated', name='automationstatusenum'), default='Not Automated'),
        sa.Column('automation_script_link', sa.String(500), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('last_modified_by_id', sa.Integer(), nullable=True),
        sa.Column('deleted_by_id', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_modified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['deleted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('test_case_id', name='uq_test_cases_id'),
    )
    op.create_index('ix_test_cases_test_case_id', 'test_cases', ['test_case_id'])
    op.create_index('ix_test_cases_status', 'test_cases', ['status'])
    op.create_index('ix_test_cases_priority', 'test_cases', ['priority'])
    
    # Create test_steps table
    op.create_table(
        'test_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_case_id', sa.Integer(), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('test_data', sa.Text(), nullable=True),
        sa.Column('expected_result', sa.Text(), nullable=False),
        sa.Column('actual_result', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('Pending', 'Pass', 'Fail', 'Blocked', 'Skipped', name='stepstatusenum'), default='Pending'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('test_case_id', 'step_number', name='uq_test_steps_number'),
    )
    op.create_index('ix_test_steps_test_case_id', 'test_steps', ['test_case_id'])
    
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('color', sa.String(7), default='#3498db'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_tags_name'),
    )
    
    # Create test_case_tags association table
    op.create_table(
        'test_case_tags',
        sa.Column('test_case_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('test_case_id', 'tag_id'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
    )
    
    # Create test_executions table
    op.create_table(
        'test_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_case_id', sa.Integer(), nullable=False),
        sa.Column('execution_date', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('duration', sa.Integer(), nullable=True),  # in seconds
        sa.Column('status', sa.Enum('Pass', 'Fail', 'Blocked', 'Skipped', name='stepstatusenum'), default='Pending'),
        sa.Column('passed_steps', sa.Integer(), default=0),
        sa.Column('failed_steps', sa.Integer(), default=0),
        sa.Column('blocked_steps', sa.Integer(), default=0),
        sa.Column('skipped_steps', sa.Integer(), default=0),
        sa.Column('environment', sa.String(255), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('bug_ids', sa.String(500), nullable=True),  # comma-separated bug IDs
        sa.Column('executed_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['executed_by_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_test_executions_test_case_id', 'test_executions', ['test_case_id'])
    op.create_index('ix_test_executions_execution_date', 'test_executions', ['execution_date'])
    
    # Create test_case_attachments table
    op.create_table(
        'test_case_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_case_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),  # in bytes
        sa.Column('file_type', sa.String(100), nullable=True),  # MIME type
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_test_case_attachments_test_case_id', 'test_case_attachments', ['test_case_id'])


def downgrade() -> None:
    """Revert schema to initial state"""
    
    # Drop all new tables
    op.drop_table('test_case_attachments')
    op.drop_index('ix_test_executions_execution_date', table_name='test_executions')
    op.drop_index('ix_test_executions_test_case_id', table_name='test_executions')
    op.drop_table('test_executions')
    op.drop_table('test_case_tags')
    op.drop_table('tags')
    op.drop_index('ix_test_steps_test_case_id', table_name='test_steps')
    op.drop_table('test_steps')
    op.drop_index('ix_test_cases_priority', table_name='test_cases')
    op.drop_index('ix_test_cases_status', table_name='test_cases')
    op.drop_index('ix_test_cases_test_case_id', table_name='test_cases')
    op.drop_table('test_cases')
    
    # Recreate simple test_cases table from initial schema
    op.create_table(
        'test_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
    )
