"""
Test Suite Management - Migration 004
Adds test suite models for grouping and managing test cases

Revision ID: 004_test_suite_management
Revises: 003
Create Date: 2024-03-06
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# Revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create test suite tables"""
    
    # Create test_suites table
    op.create_table(
        'test_suites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suite_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('module', sa.String(length=100), nullable=True),
        sa.Column('parent_suite_id', sa.Integer(), nullable=True),
        sa.Column('execution_mode', sa.String(length=20), nullable=False, server_default='sequential'),
        sa.Column('estimated_duration', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_suite_id'], ['test_suites.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['deleted_by_id'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes for test_suites
    op.create_index('ix_test_suites_suite_id', 'test_suites', ['suite_id'], unique=True)
    op.create_index('ix_test_suites_name', 'test_suites', ['name'])
    op.create_index('ix_test_suites_parent_suite_id', 'test_suites', ['parent_suite_id'])
    op.create_index('ix_test_suites_project_id', 'test_suites', ['project_id'])
    op.create_index('ix_test_suites_status', 'test_suites', ['status'])
    
    # Create test_suite_test_cases association table
    op.create_table(
        'test_suite_test_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suite_id', sa.Integer(), nullable=False),
        sa.Column('test_case_id', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('added_by_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['suite_id'], ['test_suites.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by_id'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes for test_suite_test_cases
    op.create_index('ix_test_suite_test_cases_suite_id', 'test_suite_test_cases', ['suite_id'])
    op.create_index('ix_test_suite_test_cases_test_case_id', 'test_suite_test_cases', ['test_case_id'])
    op.create_index('ix_test_suite_test_cases_order', 'test_suite_test_cases', ['suite_id', 'order'])
    
    # Create test_suite_executions table
    op.create_table(
        'test_suite_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suite_id', sa.Integer(), nullable=False),
        sa.Column('execution_name', sa.String(length=200), nullable=True),
        sa.Column('executed_by_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_test_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('blocked', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('environment', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['suite_id'], ['test_suites.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['executed_by_id'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes for test_suite_executions
    op.create_index('ix_test_suite_executions_suite_id', 'test_suite_executions', ['suite_id'])
    op.create_index('ix_test_suite_executions_status', 'test_suite_executions', ['status'])
    op.create_index('ix_test_suite_executions_started_at', 'test_suite_executions', ['started_at'])


def downgrade():
    """Drop test suite tables"""
    
    # Drop indexes
    op.drop_index('ix_test_suite_executions_started_at', table_name='test_suite_executions')
    op.drop_index('ix_test_suite_executions_status', table_name='test_suite_executions')
    op.drop_index('ix_test_suite_executions_suite_id', table_name='test_suite_executions')
    
    op.drop_index('ix_test_suite_test_cases_order', table_name='test_suite_test_cases')
    op.drop_index('ix_test_suite_test_cases_test_case_id', table_name='test_suite_test_cases')
    op.drop_index('ix_test_suite_test_cases_suite_id', table_name='test_suite_test_cases')
    
    op.drop_index('ix_test_suites_status', table_name='test_suites')
    op.drop_index('ix_test_suites_project_id', table_name='test_suites')
    op.drop_index('ix_test_suites_parent_suite_id', table_name='test_suites')
    op.drop_index('ix_test_suites_name', table_name='test_suites')
    op.drop_index('ix_test_suites_suite_id', table_name='test_suites')
    
    # Drop tables
    op.drop_table('test_suite_executions')
    op.drop_table('test_suite_test_cases')
    op.drop_table('test_suites')
