from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLIENT = "client"


class ProjectStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PENDING_APPROVAL = "pending_approval"
    PAID = "paid"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workspace = relationship("Workspace", back_populates="users")
    projects = relationship("Project", back_populates="client", foreign_keys="Project.client_id")
    comments = relationship("Comment", back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    owner_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="workspace")
    projects = relationship("Project", back_populates="workspace")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    client_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PENDING)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.UNPAID)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workspace = relationship("Workspace", back_populates="projects")
    client = relationship("User", back_populates="projects", foreign_keys=[client_id])
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")
    updates = relationship("ProjectUpdate", back_populates="project", cascade="all, delete-orphan")


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(String, nullable=False)  # Stored as string like "2MB"
    file_category = Column(String, nullable=False)  # "client" or "delivery" or "update"
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)

    project = relationship("Project", back_populates="files")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="comments")
    user = relationship("User", back_populates="comments")


class ProjectUpdate(Base):
    __tablename__ = "project_updates"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="updates")
    files = relationship("ProjectFile", foreign_keys="ProjectFile.project_id", 
                         primaryjoin="and_(ProjectUpdate.project_id==ProjectFile.project_id, ProjectFile.file_category=='update')")

