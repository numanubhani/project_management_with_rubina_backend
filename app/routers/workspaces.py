from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import json
from datetime import datetime
from app.database import get_db
from app.models import Workspace, User, UserRole, Project, ProjectFile, Comment, ProjectUpdate, ProjectStatus, PaymentStatus
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


@router.get("/me/export")
async def export_workspace_data(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export complete workspace data (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can export workspace data"
        )
    
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Collect all workspace data
    users = db.query(User).filter(User.workspace_id == workspace.id).all()
    projects = db.query(Project).filter(Project.workspace_id == workspace.id).all()
    
    # Get all related data
    project_ids = [p.id for p in projects]
    comments = db.query(Comment).filter(Comment.project_id.in_(project_ids)).all() if project_ids else []
    updates = db.query(ProjectUpdate).filter(ProjectUpdate.project_id.in_(project_ids)).all() if project_ids else []
    files = db.query(ProjectFile).filter(ProjectFile.project_id.in_(project_ids)).all() if project_ids else []
    
    # Prepare export data
    export_data = {
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "code": workspace.code,
            "owner_id": workspace.owner_id,
            "created_at": workspace.created_at.isoformat() if workspace.created_at else None
        },
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ],
        "projects": [
            {
                "id": p.id,
                "client_id": p.client_id,
                "title": p.title,
                "description": p.description,
                "amount": p.amount,
                "deadline": p.deadline.isoformat() if p.deadline else None,
                "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                "payment_status": p.payment_status.value if hasattr(p.payment_status, 'value') else str(p.payment_status),
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in projects
        ],
        "comments": [
            {
                "id": c.id,
                "project_id": c.project_id,
                "user_id": c.user_id,
                "text": c.text,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in comments
        ],
        "updates": [
            {
                "id": u.id,
                "project_id": u.project_id,
                "text": u.text,
                "is_read": u.is_read,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in updates
        ],
        "files": [
            {
                "id": f.id,
                "project_id": f.project_id,
                "file_name": f.file_name,
                "file_path": f.file_path,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "file_category": f.file_category,
                "uploaded_by": f.uploaded_by,
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None
            }
            for f in files
        ],
        "export_date": datetime.now().isoformat(),
        "export_version": "1.0"
    }
    
    # Return JSON response with proper headers for download
    from fastapi.responses import Response
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
    filename = f"workspace_export_{workspace.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return Response(
        content=json_str,
        media_type='application/json',
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/me/import")
async def import_workspace_data(
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Import workspace data from exported file (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can import workspace data"
        )
    
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Read and parse JSON file
    try:
        content = await file.read()
        import_data = json.loads(content.decode('utf-8'))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format: {str(e)}"
        )
    
    # Validate export version
    if import_data.get("export_version") != "1.0":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export version"
        )
    
    try:
        # Import users (skip if email already exists)
        imported_users = {}
        for user_data in import_data.get("users", []):
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing_user:
                # Create new user (without password - they'll need to reset)
                new_user = User(
                    id=user_data["id"],
                    name=user_data["name"],
                    email=user_data["email"],
                    hashed_password="",  # Password needs to be reset
                    role=UserRole(user_data["role"]),
                    workspace_id=workspace.id
                )
                db.add(new_user)
                imported_users[user_data["id"]] = new_user
        
        db.flush()
        
        # Import projects
        for project_data in import_data.get("projects", []):
            existing_project = db.query(Project).filter(Project.id == project_data["id"]).first()
            if not existing_project:
                # Map client_id to new user if needed, otherwise use existing user
                client_id = project_data["client_id"]
                if client_id in imported_users:
                    client_id = imported_users[client_id].id
                else:
                    # Check if user exists in current workspace
                    existing_client = db.query(User).filter(
                        User.id == client_id,
                        User.workspace_id == workspace.id
                    ).first()
                    if not existing_client:
                        continue  # Skip project if client doesn't exist
                
                new_project = Project(
                    id=project_data["id"],
                    workspace_id=workspace.id,
                    client_id=client_id,
                    title=project_data["title"],
                    description=project_data["description"],
                    amount=project_data["amount"],
                    deadline=datetime.fromisoformat(project_data["deadline"]) if project_data.get("deadline") else None,
                    status=ProjectStatus(project_data["status"]),
                    payment_status=PaymentStatus(project_data["payment_status"]),
                    paid_at=datetime.fromisoformat(project_data["paid_at"]) if project_data.get("paid_at") else None
                )
                db.add(new_project)
        
        db.flush()
        
        # Import comments
        for comment_data in import_data.get("comments", []):
            existing_comment = db.query(Comment).filter(Comment.id == comment_data["id"]).first()
            if not existing_comment:
                # Map user_id to new user if needed, otherwise use existing user
                user_id = comment_data["user_id"]
                if user_id in imported_users:
                    user_id = imported_users[user_id].id
                else:
                    # Check if user exists in current workspace
                    existing_user = db.query(User).filter(
                        User.id == user_id,
                        User.workspace_id == workspace.id
                    ).first()
                    if not existing_user:
                        continue  # Skip comment if user doesn't exist
                
                # Check if project exists
                project_exists = db.query(Project).filter(Project.id == comment_data["project_id"]).first()
                if not project_exists:
                    continue  # Skip comment if project doesn't exist
                
                new_comment = Comment(
                    id=comment_data["id"],
                    project_id=comment_data["project_id"],
                    user_id=user_id,
                    text=comment_data["text"]
                )
                db.add(new_comment)
        
        # Import updates
        for update_data in import_data.get("updates", []):
            existing_update = db.query(ProjectUpdate).filter(ProjectUpdate.id == update_data["id"]).first()
            if not existing_update:
                new_update = ProjectUpdate(
                    id=update_data["id"],
                    project_id=update_data["project_id"],
                    text=update_data["text"],
                    is_read=update_data.get("is_read", False)
                )
                db.add(new_update)
        
        # Import file metadata (actual files would need to be uploaded separately)
        for file_data in import_data.get("files", []):
            existing_file = db.query(ProjectFile).filter(ProjectFile.id == file_data["id"]).first()
            if not existing_file:
                # Map uploaded_by to new user if needed, otherwise use existing user
                uploaded_by = file_data["uploaded_by"]
                if uploaded_by in imported_users:
                    uploaded_by = imported_users[uploaded_by].id
                else:
                    # Check if user exists in current workspace
                    existing_user = db.query(User).filter(
                        User.id == uploaded_by,
                        User.workspace_id == workspace.id
                    ).first()
                    if not existing_user:
                        continue  # Skip file if user doesn't exist
                
                # Check if project exists
                project_exists = db.query(Project).filter(Project.id == file_data["project_id"]).first()
                if not project_exists:
                    continue  # Skip file if project doesn't exist
                
                new_file = ProjectFile(
                    id=file_data["id"],
                    project_id=file_data["project_id"],
                    file_name=file_data["file_name"],
                    file_path=file_data["file_path"],
                    file_type=file_data["file_type"],
                    file_size=file_data["file_size"],
                    file_category=file_data["file_category"],
                    uploaded_by=uploaded_by
                )
                db.add(new_file)
        
        db.commit()
        
        return {
            "message": "Workspace data imported successfully",
            "imported_users": len(imported_users),
            "imported_projects": len(import_data.get("projects", [])),
            "imported_comments": len(import_data.get("comments", [])),
            "imported_updates": len(import_data.get("updates", [])),
            "imported_files": len(import_data.get("files", []))
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )

