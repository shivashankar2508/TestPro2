"""Add advanced test case features (owner, version history, templates, import batches)

Revision ID: 003_test_case_advanced_features
Revises: 002_extend_test_case_schema
Create Date: 2026-03-02 13:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_test_case_advanced_features"
down_revision: Union[str, None] = "002_extend_test_case_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ownership and assignment columns
    op.add_column("test_cases", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.add_column("test_cases", sa.Column("assigned_tester_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_test_cases_owner_id_users",
        "test_cases",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_test_cases_assigned_tester_id_users",
        "test_cases",
        "users",
        ["assigned_tester_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Backfill owner with created_by
    op.execute("UPDATE test_cases SET owner_id = created_by_id WHERE owner_id IS NULL")

    # Version history table
    op.create_table(
        "test_case_version_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_case_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=False),
        sa.Column("changed_fields", sa.Text(), nullable=True),
        sa.Column("changed_by_id", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_case_version_history_id", "test_case_version_history", ["id"])
    op.create_index("ix_test_case_version_history_test_case_id", "test_case_version_history", ["test_case_id"])

    # Template library table
    op.create_table(
        "test_case_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_test_case_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_test_case_id"], ["test_cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_case_templates_id", "test_case_templates", ["id"])
    op.create_index("ix_test_case_templates_category", "test_case_templates", ["category"])

    # Import preview/confirm batch storage
    op.create_table(
        "test_case_import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("field_mapping", sa.Text(), nullable=True),
        sa.Column("preview_payload", sa.Text(), nullable=False),
        sa.Column("validation_errors", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_case_import_batches_id", "test_case_import_batches", ["id"])


def downgrade() -> None:
    op.drop_index("ix_test_case_import_batches_id", table_name="test_case_import_batches")
    op.drop_table("test_case_import_batches")

    op.drop_index("ix_test_case_templates_category", table_name="test_case_templates")
    op.drop_index("ix_test_case_templates_id", table_name="test_case_templates")
    op.drop_table("test_case_templates")

    op.drop_index("ix_test_case_version_history_test_case_id", table_name="test_case_version_history")
    op.drop_index("ix_test_case_version_history_id", table_name="test_case_version_history")
    op.drop_table("test_case_version_history")

    op.drop_constraint("fk_test_cases_assigned_tester_id_users", "test_cases", type_="foreignkey")
    op.drop_constraint("fk_test_cases_owner_id_users", "test_cases", type_="foreignkey")
    op.drop_column("test_cases", "assigned_tester_id")
    op.drop_column("test_cases", "owner_id")
