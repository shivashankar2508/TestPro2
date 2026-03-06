from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

# ============ Enums ============
class RoleEnum(str, enum.Enum):
    TESTER = "tester"
    DEVELOPER = "developer"
    ADMIN = "admin"

class UserStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING_VERIFICATION = "pending_verification"

class IssueStatusEnum(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    WON_T_FIX = "won_t_fix"
    REOPENED = "reopened"
    CLOSED = "closed"

# ============ User Models ============
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=False)  # Requires email verification
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True, unique=True)
    verification_token_expiry = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Account security
    role = Column(String(50), default=RoleEnum.TESTER.value, nullable=False)
    status = Column(String(50), default=UserStatusEnum.PENDING_VERIFICATION.value)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # OAuth
    google_id = Column(String(255), nullable=True, unique=True)
    github_id = Column(String(255), nullable=True, unique=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    password_history = relationship("PasswordHistory", back_populates="user", cascade="all, delete-orphan")
    oauth_providers = relationship("OAuthProvider", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", foreign_keys="Project.created_by_id", back_populates="created_by")
    created_test_cases = relationship("TestCase", foreign_keys="TestCase.created_by_id", back_populates="created_by")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('email', name='uq_users_email'),
        UniqueConstraint('username', name='uq_users_username'),
    )

# ============ Password History ============
class PasswordHistory(Base):
    __tablename__ = "password_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="password_history")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'hashed_password', name='uq_password_history'),
    )

# ============ OAuth Models ============
class OAuthProvider(Base):
    __tablename__ = "oauth_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)  # google, github
    provider_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship back to User
    user = relationship("User", back_populates="oauth_providers")
    
    __table_args__ = (
        UniqueConstraint('provider', 'provider_id', name='uq_oauth_provider_id'),
    )

# ============ Session & Token ============
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
# ============ Audit Log ============
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)  # login, logout, password_change, etc.
    resource_type = Column(String(100), nullable=True)  # user, test_case, etc.
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 and IPv6
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="audit_logs")

# ============ Permission Model ============
class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)  # e.g., "users.create", "projects.delete"
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # e.g., "users", "projects", "system", "backups"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


# ============ Role Permission Model ============
class RolePermission(Base):
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False)  # admin, developer, tester, custom
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    permission = relationship("Permission", back_populates="role_permissions")
    granted_by = relationship("User", foreign_keys=[granted_by_id])
    
    __table_args__ = (
        UniqueConstraint('role', 'permission_id', name='unique_role_permission'),
    )


# ============ System Configuration Model ============
class SystemConfiguration(Base):
    __tablename__ = "system_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    data_type = Column(String(50), default="string")  # string, int, boolean, json
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    updated_by = relationship("User", foreign_keys=[updated_by_id])


# ============ Backup Model ============
class Backup(Base):
    __tablename__ = "backups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    backup_type = Column(String(50), nullable=False)  # full, incremental, test_cases
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    backup_date = Column(DateTime, default=datetime.utcnow)
    triggered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    restore_date = Column(DateTime, nullable=True)
    restored_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    triggered_by = relationship("User", foreign_keys=[triggered_by_id])
    restored_by = relationship("User", foreign_keys=[restored_by_id])


# ============ Project Model ============
class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, archived, inactive
    lead_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lead = relationship("User", foreign_keys=[lead_id])
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="projects")
    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    project_members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")


# ============ Project Member Model ============
class ProjectMember(Base):
    __tablename__ = "project_members"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), default="member")  # lead, tester, viewer, member
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="project_members")
    user = relationship("User", foreign_keys=[user_id])
    added_by = relationship("User", foreign_keys=[added_by_id])
    
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='unique_project_member'),
    )

