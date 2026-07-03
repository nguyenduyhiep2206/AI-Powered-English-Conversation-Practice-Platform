from sqlalchemy import (
    Column, String, Boolean, BigInteger, TIMESTAMP,
    Table, ForeignKey, func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


#  Junction tables (many-to-many)

user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


# roles

class RoleDB(Base):
    __tablename__ = "roles"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    name        = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    permissions = relationship("PermissionDB", secondary="role_permissions", back_populates="roles")
    users       = relationship("UserDB", secondary="user_roles", back_populates="roles")


# permissions

class PermissionDB(Base):
    __tablename__ = "permissions"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    name        = Column(String(100), nullable=False)
    code        = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    roles = relationship("RoleDB", secondary="role_permissions", back_populates="permissions")


# refresh_tokens

class RefreshTokenDB(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti        = Column(String(128), unique=True, index=True, nullable=False)
    revoked    = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expired_at = Column(TIMESTAMP(timezone=True), nullable=False)

    user = relationship("UserDB", back_populates="refresh_tokens")