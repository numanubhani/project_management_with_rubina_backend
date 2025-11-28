from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import Workspace, User, UserRole
from app.schemas import WorkspaceResponse
from app.auth import get_current_active_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None


@router.get("/me", response_model=WorkspaceResponse)
async def get_current_workspace(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's workspace information"""
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workspace by ID (must be in same workspace)"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Verify user has access to this workspace
    if workspace.id != current_user.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return workspace


@router.put("/me", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_data: WorkspaceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update workspace (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update workspace"
        )
    
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    if workspace_data.name:
        workspace.name = workspace_data.name
    
    db.commit()
    db.refresh(workspace)
    
    return workspace


@router.get("/me/stats")
async def get_workspace_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workspace statistics (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view workspace statistics"
        )
    
    from app.models import Project, User as UserModel
    
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Get statistics
    total_users = db.query(UserModel).filter(UserModel.workspace_id == workspace.id).count()
    total_projects = db.query(Project).filter(Project.workspace_id == workspace.id).count()
    active_projects = db.query(Project).filter(
        Project.workspace_id == workspace.id,
        Project.status.in_(["pending", "in_progress", "delivered"])
    ).count()
    
    return {
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "workspace_code": workspace.code,
        "total_users": total_users,
        "total_projects": total_projects,
        "active_projects": active_projects,
        "created_at": workspace.created_at.isoformat() if workspace.created_at else None
    }

