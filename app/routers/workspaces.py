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
    try:
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
        
        # Get all related data - handle empty project_ids safely
        project_ids = [p.id for p in projects]
        comments = []
        updates = []
        files = []
        
        if project_ids:
            try:
                comments = db.query(Comment).filter(Comment.project_id.in_(project_ids)).all()
            except Exception:
                comments = []
            
            try:
                updates = db.query(ProjectUpdate).filter(ProjectUpdate.project_id.in_(project_ids)).all()
            except Exception:
                updates = []
            
            try:
                files = db.query(ProjectFile).filter(ProjectFile.project_id.in_(project_ids)).all()
            except Exception:
                files = []
        
        # Prepare export data with safe serialization
        def safe_isoformat(dt):
            if dt is None:
                return None
            try:
                return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            except Exception:
                return None
        
        def safe_enum_value(enum_val):
            if enum_val is None:
                return None
            try:
                return enum_val.value if hasattr(enum_val, 'value') else str(enum_val)
            except Exception:
                return str(enum_val) if enum_val else None
        
        export_data = {
            "workspace": {
                "id": str(workspace.id) if workspace.id else None,
                "name": str(workspace.name) if workspace.name else "",
                "code": str(workspace.code) if workspace.code else "",
                "owner_id": str(workspace.owner_id) if workspace.owner_id else None,
                "created_at": safe_isoformat(workspace.created_at)
            },
            "users": [
                {
                    "id": str(u.id) if u.id else None,
                    "name": str(u.name) if u.name else "",
                    "email": str(u.email) if u.email else "",
                    "role": safe_enum_value(u.role),
                    "created_at": safe_isoformat(u.created_at)
                }
                for u in users
            ],
            "projects": [
                {
                    "id": str(p.id) if p.id else None,
                    "client_id": str(p.client_id) if p.client_id else None,
                    "title": str(p.title) if p.title else "",
                    "description": str(p.description) if p.description else "",
                    "amount": float(p.amount) if p.amount else 0.0,
                    "deadline": safe_isoformat(p.deadline),
                    "status": safe_enum_value(p.status),
                    "payment_status": safe_enum_value(p.payment_status),
                    "paid_at": safe_isoformat(p.paid_at),
                    "created_at": safe_isoformat(p.created_at)
                }
                for p in projects
            ],
            "comments": [
                {
                    "id": str(c.id) if c.id else None,
                    "project_id": str(c.project_id) if c.project_id else None,
                    "user_id": str(c.user_id) if c.user_id else None,
                    "text": str(c.text) if c.text else "",
                    "created_at": safe_isoformat(c.created_at)
                }
                for c in comments
            ],
            "updates": [
                {
                    "id": str(u.id) if u.id else None,
                    "project_id": str(u.project_id) if u.project_id else None,
                    "text": str(u.text) if u.text else "",
                    "is_read": bool(u.is_read) if u.is_read is not None else False,
                    "created_at": safe_isoformat(u.created_at)
                }
                for u in updates
            ],
            "files": [
                {
                    "id": str(f.id) if f.id else None,
                    "project_id": str(f.project_id) if f.project_id else None,
                    "file_name": str(f.file_name) if f.file_name else "",
                    "file_path": str(f.file_path) if f.file_path else "",
                    "file_type": str(f.file_type) if f.file_type else "",
                    "file_size": str(f.file_size) if f.file_size else "",
                    "file_category": str(f.file_category) if f.file_category else "",
                    "uploaded_by": str(f.uploaded_by) if f.uploaded_by else None,
                    "uploaded_at": safe_isoformat(f.uploaded_at)
                }
                for f in files
            ],
            "export_date": datetime.now().isoformat(),
            "export_version": "1.0"
        }
        
        # Return JSON response with proper headers for download
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
        filename = f"workspace_export_{workspace.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return Response(
            content=json_str.encode('utf-8'),
            media_type='application/json',
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
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
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        import_data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format: {str(e)}"
        )
    
    # Validate export version
    if not isinstance(import_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file structure"
        )
    
    if import_data.get("export_version") != "1.0":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export version"
        )
    
    try:
        # Import users (skip if email already exists)
        imported_users = {}
        for user_data in import_data.get("users", []):
            if not isinstance(user_data, dict) or not user_data.get("email"):
                continue
            try:
                existing_user = db.query(User).filter(User.email == user_data["email"]).first()
                if not existing_user:
                    # Create new user (without password - they'll need to reset)
                    new_user = User(
                        id=str(user_data.get("id", "")),
                        name=str(user_data.get("name", "")),
                        email=str(user_data.get("email", "")),
                        hashed_password="",  # Password needs to be reset
                        role=UserRole(user_data.get("role", "client")),
                        workspace_id=workspace.id
                    )
                    db.add(new_user)
                    imported_users[str(user_data.get("id", ""))] = new_user
            except Exception:
                # Skip invalid user data
                continue
        
        db.flush()
        
        # Import projects
        for project_data in import_data.get("projects", []):
            if not isinstance(project_data, dict) or not project_data.get("id"):
                continue
            try:
                existing_project = db.query(Project).filter(Project.id == project_data["id"]).first()
                if not existing_project:
                    # Map client_id to new user if needed, otherwise use existing user
                    client_id = str(project_data.get("client_id", ""))
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
                    
                    # Parse deadline safely
                    deadline = None
                    if project_data.get("deadline"):
                        try:
                            deadline = datetime.fromisoformat(project_data["deadline"].replace('Z', '+00:00'))
                        except:
                            try:
                                deadline = datetime.fromisoformat(project_data["deadline"])
                            except:
                                deadline = None
                    
                    # Parse paid_at safely
                    paid_at = None
                    if project_data.get("paid_at"):
                        try:
                            paid_at = datetime.fromisoformat(project_data["paid_at"].replace('Z', '+00:00'))
                        except:
                            try:
                                paid_at = datetime.fromisoformat(project_data["paid_at"])
                            except:
                                paid_at = None
                    
                    new_project = Project(
                        id=str(project_data.get("id", "")),
                        workspace_id=workspace.id,
                        client_id=client_id,
                        title=str(project_data.get("title", "")),
                        description=str(project_data.get("description", "")),
                        amount=float(project_data.get("amount", 0.0)),
                        deadline=deadline,
                        status=ProjectStatus(project_data.get("status", "pending")),
                        payment_status=PaymentStatus(project_data.get("payment_status", "unpaid")),
                        paid_at=paid_at
                    )
                    db.add(new_project)
            except Exception as e:
                # Skip invalid project data
                continue
        
        db.flush()
        
        # Import comments
        for comment_data in import_data.get("comments", []):
            if not isinstance(comment_data, dict) or not comment_data.get("id"):
                continue
            try:
                existing_comment = db.query(Comment).filter(Comment.id == comment_data.get("id")).first()
                if not existing_comment:
                    # Map user_id to new user if needed, otherwise use existing user
                    user_id = str(comment_data.get("user_id", ""))
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
                    project_exists = db.query(Project).filter(Project.id == comment_data.get("project_id")).first()
                    if not project_exists:
                        continue  # Skip comment if project doesn't exist
                    
                    new_comment = Comment(
                        id=str(comment_data.get("id", "")),
                        project_id=str(comment_data.get("project_id", "")),
                        user_id=user_id,
                        text=str(comment_data.get("text", ""))
                    )
                    db.add(new_comment)
            except Exception:
                # Skip invalid comment data
                continue
        
        # Import updates
        for update_data in import_data.get("updates", []):
            if not isinstance(update_data, dict) or not update_data.get("id"):
                continue
            try:
                existing_update = db.query(ProjectUpdate).filter(ProjectUpdate.id == update_data.get("id")).first()
                if not existing_update:
                    # Check if project exists
                    project_exists = db.query(Project).filter(Project.id == update_data.get("project_id")).first()
                    if not project_exists:
                        continue  # Skip update if project doesn't exist
                    
                    new_update = ProjectUpdate(
                        id=str(update_data.get("id", "")),
                        project_id=str(update_data.get("project_id", "")),
                        text=str(update_data.get("text", "")),
                        is_read=bool(update_data.get("is_read", False))
                    )
                    db.add(new_update)
            except Exception:
                # Skip invalid update data
                continue
        
        # Import file metadata (actual files would need to be uploaded separately)
        for file_data in import_data.get("files", []):
            if not isinstance(file_data, dict) or not file_data.get("id"):
                continue
            try:
                existing_file = db.query(ProjectFile).filter(ProjectFile.id == file_data.get("id")).first()
                if not existing_file:
                    # Map uploaded_by to new user if needed, otherwise use existing user
                    uploaded_by = str(file_data.get("uploaded_by", ""))
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
                    project_exists = db.query(Project).filter(Project.id == file_data.get("project_id")).first()
                    if not project_exists:
                        continue  # Skip file if project doesn't exist
                    
                    new_file = ProjectFile(
                        id=str(file_data.get("id", "")),
                        project_id=str(file_data.get("project_id", "")),
                        file_name=str(file_data.get("file_name", "")),
                        file_path=str(file_data.get("file_path", "")),
                        file_type=str(file_data.get("file_type", "")),
                        file_size=str(file_data.get("file_size", "")),
                        file_category=str(file_data.get("file_category", "")),
                        uploaded_by=uploaded_by
                    )
                    db.add(new_file)
            except Exception:
                # Skip invalid file data
                continue
        
        db.commit()
        
        # Count successfully imported items (only count what was actually added)
        imported_projects_list = [p.get("id") for p in import_data.get("projects", []) if isinstance(p, dict) and p.get("id")]
        imported_comments_list = [c.get("id") for c in import_data.get("comments", []) if isinstance(c, dict) and c.get("id")]
        imported_updates_list = [u.get("id") for u in import_data.get("updates", []) if isinstance(u, dict) and u.get("id")]
        imported_files_list = [f.get("id") for f in import_data.get("files", []) if isinstance(f, dict) and f.get("id")]
        
        imported_projects_count = 0
        imported_comments_count = 0
        imported_updates_count = 0
        imported_files_count = 0
        
        if imported_projects_list:
            try:
                imported_projects_count = db.query(Project).filter(Project.id.in_(imported_projects_list)).count()
            except:
                pass
        
        if imported_comments_list:
            try:
                imported_comments_count = db.query(Comment).filter(Comment.id.in_(imported_comments_list)).count()
            except:
                pass
        
        if imported_updates_list:
            try:
                imported_updates_count = db.query(ProjectUpdate).filter(ProjectUpdate.id.in_(imported_updates_list)).count()
            except:
                pass
        
        if imported_files_list:
            try:
                imported_files_count = db.query(ProjectFile).filter(ProjectFile.id.in_(imported_files_list)).count()
            except:
                pass
        
        return {
            "message": "Workspace data imported successfully",
            "imported_users": len(imported_users),
            "imported_projects": imported_projects_count,
            "imported_comments": imported_comments_count,
            "imported_updates": imported_updates_count,
            "imported_files": imported_files_count
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e) if e else "Unknown error"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {error_msg}"
        )

