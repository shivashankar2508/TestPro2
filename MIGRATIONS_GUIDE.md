# Database Migrations Guide - TestTrack Pro

## Overview

Alembic is a lightweight database migration tool that manages schema changes. It allows us to:

- **Version control** database changes
- **Collaborate** on schema modifications
- **Deploy** changes to different environments
- **Rollback** to previous versions if needed
- **Track history** of all schema changes

## Setup

### 1. Alembic Installation

Alembic is already in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Directory Structure

```
backend/
├── migrations/
│   ├── versions/
│   │   ├── 001_initial_schema.py      # Initial schema migration
│   │   └── (more migrations...)
│   ├── env.py                          # Alembic environment config
│   ├── script.py.mako                  # Migration template
│   └── __init__.py
├── alembic.ini                         # Alembic configuration
└── app/
```

### 3. Configuration

The `alembic.ini` file contains:
- Database connection settings
- Logging configuration
- Migration file locations

The `migrations/env.py` file:
- Loads environment variables
- Imports database models
- Configures migration runner (online/offline modes)

## Migration Commands

### Create a New Migration

```bash
# Auto-generate migration based on model changes
alembic revision --autogenerate -m "Add new column to users table"

# Create empty migration template
alembic revision -m "Custom migration description"
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply next migration
alembic upgrade +1

# Apply specific migration
alembic upgrade 001_initial_schema

# Apply migrations up to specific version
alembic upgrade 003_add_test_executions
```

### Rollback Migrations

```bash
# Rollback to previous migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Rollback to specific migration
alembic downgrade 001_initial_schema
```

### View Migration History

```bash
# Show current database version
alembic current

# Show all migrations
alembic history
```

## Migration Files

### Structure of a Migration File

```python
"""Add new column to users table

Revision ID: 002_add_phone_to_users
Revises: 001_initial_schema
Create Date: 2026-03-02 10:15:00
"""

from alembic import op
import sqlalchemy as sa

revision = "002_add_phone_to_users"
down_revision = "001_initial_schema"

def upgrade() -> None:
    """Add phone column"""
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

def downgrade() -> None:
    """Remove phone column"""
    op.drop_column('users', 'phone')
```

### Key Alembic Operations

**Column Operations:**
```python
# Add column
op.add_column('table_name', sa.Column('column_name', sa.String(50)))

# Drop column
op.drop_column('table_name', 'column_name')

# Modify column type
op.alter_column('table_name', 'column_name', type_=sa.Integer())

# Rename column
op.alter_column('table_name', 'old_name', new_column_name='new_name')
```

**Table Operations:**
```python
# Create table
op.create_table('table_name',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('name', sa.String(255)),
)

# Drop table
op.drop_table('table_name')

# Rename table
op.rename_table('old_name', 'new_name')
```

**Index/Constraint Operations:**
```python
# Create index
op.create_index('ix_users_email', 'users', ['email'])

# Drop index
op.drop_index('ix_users_email', table_name='users')

# Add constraint
op.create_unique_constraint('uq_users_email', 'users', ['email'])

# Drop constraint
op.drop_constraint('uq_users_email', 'users')
```

## Workflow

### 1. Initial Schema (Already Done)

The initial migration (`001_initial_schema.py`) creates all tables:
- users
- password_history
- refresh_tokens
- oauth_providers
- audit_logs
- projects
- test_cases

### 2. Adding New Features

**Example: Add phone and address fields to users**

Step 1: Update model
```python
# app/models/user.py
class User(Base):
    # ... existing fields
    phone = Column(String(20), nullable=True)
    address = Column(Text(), nullable=True)
```

Step 2: Create migration
```bash
alembic revision --autogenerate -m "Add phone and address to users"
```

Step 3: Review generated migration
```python
# migrations/versions/002_add_phone_address.py
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('address', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('users', 'address')
    op.drop_column('users', 'phone')
```

Step 4: Apply migration
```bash
alembic upgrade head
```

### 3. Renaming/Modifying Columns

**Example: Rename `full_name` to `display_name`**

```bash
alembic revision -m "Rename full_name to display_name"
```

Edit the migration:
```python
def upgrade():
    op.alter_column('users', 'full_name', new_column_name='display_name')

def downgrade():
    op.alter_column('users', 'display_name', new_column_name='full_name')
```

Apply:
```bash
alembic upgrade head
```

## Best Practices

### ✅ DO

1. **Create migrations for schema changes**
   - Never modify database directly
   - Always use migrations

2. **Use descriptive migration names**
   ```
   002_add_test_execution_table.py      ✅ Good
   002_changes.py                        ❌ Bad
   ```

3. **Keep migrations small and focused**
   - One feature per migration
   - Easier to debug and rollback

4. **Test migrations locally first**
   ```bash
   # Test upgrade
   alembic upgrade head
   
   # Test downgrade
   alembic downgrade -1
   
   # Test upgrade again
   alembic upgrade head
   ```

5. **Use reversible migrations**
   - Always implement both `upgrade()` and `downgrade()`
   - Allows rolling back if needed

6. **Document complex migrations**
   ```python
   """Add test_execution_status enum and migrate data
   
   This migration:
   1. Creates new ENUM type
   2. Adds column to test_executions
   3. Migrates existing data
   4. Adds NOT NULL constraint
   """
   ```

### ❌ DON'T

1. **Don't modify migrations after merging**
   - Creates inconsistency in shared repos
   - Create new migration to fix issues

2. **Don't skip migrations in development**
   - Always apply migrations sequentially
   - Prevents "works on my machine" issues

3. **Don't mix model and data migrations**
   - Schema changes in one migration
   - Data migrations in separate migration

4. **Don't delete migration files**
   - Alembic tracks history by filename
   - Breaks migration chain for others

## Deployment

### Production Migration Process

```bash
# 1. Backup database
pg_dump testtrack_pro > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Show pending migrations
alembic history

# 3. Apply migrations
alembic upgrade head

# 4. Verify success
alembic current

# 5. Monitor application
# Watch logs for any errors

# If error: Rollback
alembic downgrade -1
```

### Docker Deployment

In `docker-compose.yml`:
```yaml
backend:
  build: ./backend
  command: bash -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0"
```

### CI/CD Pipeline

```yaml
# .github/workflows/migrations.yml
- name: Verify migrations
  run: |
    alembic upgrade head --sql  # Preview SQL without applying
    alembic current
```

## Troubleshooting

### Issue: "Can't locate revision identified by..."

**Cause:** Migration files deleted or moved

**Solution:** Check migration history
```bash
alembic history
# Check migrations/versions/ directory matches history
```

### Issue: "Target database is not up to date"

**Cause:** Migrations were applied outside of Alembic

**Solution:** Mark as applied
```bash
alembic stamp head  # Mark all as applied (use carefully!)
```

### Issue: "Foreign key constraint fails" during migration

**Cause:** Trying to alter column with foreign keys

**Solution:** Drop/recreate dependencies first
```python
def upgrade():
    # Drop dependent foreign keys
    op.drop_constraint('fk_col', 'dependent_table')
    
    # Modify column
    op.alter_column('original_table', 'col', type_=sa.String(50))
    
    # Recreate foreign key
    op.create_foreign_key('fk_col', 'dependent_table', ...)
```

### Issue: "Can't execute downgrade" - Operation not reversible

**Cause:** Downgrade function not implemented

**Solution:** Implement downgrade properly
```python
def downgrade():
    """Must reverse the upgrade changes"""
    op.drop_table('new_table')  # or appropriate reversal
```

## Migration Examples

### Example 1: Add New Table

```python
"""Create bug_reports table

Revision ID: 003_create_bug_reports
Revises: 002_add_phone_address
"""

def upgrade():
    op.create_table(
        'bug_reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('test_case_id', sa.Integer()),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text()),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical')),
        sa.Column('status', sa.String(50)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id']),
    )

def downgrade():
    op.drop_table('bug_reports')
```

### Example 2: Add Column with Default

```python
"""Add priority to projects

Revision ID: 004_add_project_priority
Revises: 003_create_bug_reports
"""

def upgrade():
    op.add_column('projects', 
        sa.Column('priority', sa.Integer(), default=0, nullable=False)
    )

def downgrade():
    op.drop_column('projects', 'priority')
```

### Example 3: Modify Column Type

```python
"""Change version from string to integer

Revision ID: 005_change_version_type
Revises: 004_add_project_priority
"""

def upgrade():
    # PostgreSQL specific: use USING clause
    op.execute("ALTER TABLE projects ALTER COLUMN version TYPE INTEGER USING version::INTEGER")

def downgrade():
    op.alter_column('projects', 'version', type_=sa.String(50))
```

## Integration with Version Control

### `.gitignore`

```
# Alembic dynamic files
migrations/versions/*
!migrations/versions/.gitkeep

# Database files
*.db
*.sqlite
```

### Committing Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add user preferences table"

# Review changes
git diff migrations/versions/

# Commit with explanation
git commit -m "Migration: Add user preferences table

- New preferences table for storing user settings
- Links to users via user_id foreign key
- Includes indices on user_id and setting_key"
```

## Advanced Topics

### Custom Migration Functions

```python
"""Data migration with custom logic

Revision ID: 006_migrate_user_roles
"""

def upgrade():
    # Create new column
    op.add_column('users', sa.Column('new_role', sa.String(50)))
    
    # Bind session to migrate data
    bind = op.get_bind()
    session = Session(bind=bind)
    
    # Migrate data
    for user in session.query(User).all():
        user.new_role = 'admin' if user.is_admin else 'user'
    
    session.commit()
    
    # Now can safely drop old column
    op.drop_column('users', 'is_admin')

def downgrade():
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), default=False))
    # Reverse data migration logic
```

### Branch Migrations (Multi-version Support)

For complex projects supporting multiple versions:

```python
# In env.py
branch_labels = ['feature1', 'feature2']

# In migration header
branch_labels = 'feature1'
```

## Testing Migrations

```bash
# Create test database
createdb testtrack_pro_test

# Install app
pip install -e backend/

# Run migrations
DATABASE_URL="postgresql://user:pass@localhost/testtrack_pro_test" alembic upgrade head

# Verify schema
psql testtrack_pro_test -c "\dt"  # List tables

# Cleanup
dropdb testtrack_pro_test
```

## Summary

Alembic provides:
- ✅ Version control for database schema
- ✅ Safe, reversible migrations  
- ✅ Team collaboration on schema changes
- ✅ Deployment confidence
- ✅ Rollback capability

Always use migrations for schema changes - never modify databases directly!

---

**Created:** March 2, 2026
**Status:** Production Ready ✅
