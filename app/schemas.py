from pydantic import BaseModel, EmailStr, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from app.models import UserRole, ProjectStatus, PaymentStatus


# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str
    workspaceId: str
    createdAt: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
        
    @classmethod
    def from_user_model(cls, user):
        """Convert User model to UserResponse with camelCase fields"""
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            workspaceId=user.workspace_id,
            createdAt=user.created_at or datetime.now()
        )


# Workspace Schemas
class WorkspaceBase(BaseModel):
    name: str
    code: str


class WorkspaceCreate(BaseModel):
    workspace_name: str
    admin_name: str
    email: EmailStr
    password: str


class WorkspaceResponse(WorkspaceBase):
    id: str
    owner_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# File Schemas
class FileData(BaseModel):
    id: str
    name: str
    url: str
    type: str
    size: str
    uploadedAt: str


# Comment Schemas
class CommentBase(BaseModel):
    text: str


class CommentCreate(CommentBase):
    pass


class CommentResponse(BaseModel):
    id: str
    userId: str
    userName: str
    text: str
    createdAt: datetime

    class Config:
        from_attributes = True


# Project Update Schemas
class ProjectUpdateBase(BaseModel):
    text: str
    files: List[FileData] = []


class ProjectUpdateCreate(BaseModel):
    text: str


class ProjectUpdateResponse(BaseModel):
    id: str
    text: str
    files: List[FileData]
    createdAt: datetime
    isRead: bool

    class Config:
        from_attributes = True


# Project Schemas
class ProjectBase(BaseModel):
    title: str
    description: str
    amount: float
    deadline: datetime


class ProjectCreate(ProjectBase):
    files: List[FileData] = []


class ProjectResponse(BaseModel):
    id: str
    workspaceId: str
    clientId: str
    title: str
    description: str
    amount: float
    createdAt: datetime
    deadline: datetime
    status: ProjectStatus
    paymentStatus: PaymentStatus
    paidAt: Optional[datetime] = None
    clientFiles: List[FileData] = []
    deliveryFiles: List[FileData] = []
    comments: List[CommentResponse] = []
    updates: List[ProjectUpdateResponse] = []

    class Config:
        from_attributes = True


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class PaymentStatusUpdate(BaseModel):
    payment_status: PaymentStatus


# Dashboard Stats
class DashboardStats(BaseModel):
    total: int
    pending: int
    active: int
    completed: int

