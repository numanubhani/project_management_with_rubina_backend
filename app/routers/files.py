from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, ProjectFile, User
from app.auth import get_current_active_user
from app.config import settings
import os

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("/{project_id}/{category}/{filename}")
async def download_file(
    project_id: str,
    category: str,
    filename: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download a project file"""
    # Verify project access
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == current_user.workspace_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check access
    if current_user.role.value == "client" and project.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Validate category
    if category not in ["client", "delivery", "update"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file category"
        )
    
    # Find file
    file_record = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.file_category == category,
        ProjectFile.file_name.contains(filename)
    ).first()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if file exists on disk
    if not os.path.exists(file_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    return FileResponse(
        file_record.file_path,
        filename=file_record.file_name,
        media_type=file_record.file_type
    )

