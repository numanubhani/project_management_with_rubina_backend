from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import (
    Project, User, ProjectFile, Comment, ProjectUpdate,
    ProjectStatus, PaymentStatus, UserRole
)
from app.schemas import (
    ProjectCreate, ProjectResponse, ProjectStatusUpdate,
    CommentCreate, CommentResponse,
    ProjectUpdateCreate, ProjectUpdateResponse, DashboardStats
)
from app.schemas import FileData
from app.auth import get_current_active_user
from app.utils import generate_id, save_multiple_files, file_data_to_schema
from app.config import settings

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def project_to_response(project: Project, current_user: User) -> ProjectResponse:
    """Convert Project model to ProjectResponse schema"""
    # Get files by category
    client_files = [
        FileData(
            id=f.id,
            name=f.file_name,
            url=f"/api/files/{project.id}/client/{f.file_name.split('/')[-1]}",
            type=f.file_type,
            size=f.file_size,
            uploadedAt=f.uploaded_at.isoformat()
        )
        for f in project.files if f.file_category == "client" and project.status != ProjectStatus.COMPLETED
    ]
    
    delivery_files = [
        FileData(
            id=f.id,
            name=f.file_name,
            url=f"/api/files/{project.id}/delivery/{f.file_name.split('/')[-1]}",
            type=f.file_type,
            size=f.file_size,
            uploadedAt=f.uploaded_at.isoformat()
        )
        for f in project.files if f.file_category == "delivery" and project.status != ProjectStatus.COMPLETED
    ]
    
    # Get comments
    comments = [
        CommentResponse(
            id=c.id,
            userId=c.user_id,
            userName=c.user.name,
            text=c.text,
            createdAt=c.created_at
        )
        for c in project.comments
    ]
    
    # Get updates
    updates = []
    for update in project.updates:
        update_files = [
            FileData(
                id=f.id,
                name=f.file_name,
                url=f"/api/files/{project.id}/update/{f.file_name.split('/')[-1]}",
                type=f.file_type,
                size=f.file_size,
                uploadedAt=f.uploaded_at.isoformat()
            )
            for f in project.files if f.file_category == "update" and f.uploaded_at >= update.created_at
        ]
        updates.append(ProjectUpdateResponse(
            id=update.id,
            text=update.text,
            files=update_files if project.status != ProjectStatus.COMPLETED else [],
            createdAt=update.created_at,
            isRead=update.is_read
        ))
    
    return ProjectResponse(
        id=project.id,
        workspaceId=project.workspace_id,
        clientId=project.client_id,
        title=project.title,
        description=project.description,
        amount=project.amount,
        createdAt=project.created_at,
        deadline=project.deadline,
        status=project.status,
        paymentStatus=project.payment_status,
        paidAt=project.paid_at,
        clientFiles=client_files,
        deliveryFiles=delivery_files,
        comments=comments,
        updates=updates
    )


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all projects for the current user"""
    query = db.query(Project).filter(Project.workspace_id == current_user.workspace_id)
    
    if current_user.role == UserRole.CLIENT:
        query = query.filter(Project.client_id == current_user.id)
    
    projects = query.order_by(Project.deadline.asc()).all()
    return [project_to_response(p, current_user) for p in projects]


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    query = db.query(Project).filter(Project.workspace_id == current_user.workspace_id)
    
    if current_user.role == UserRole.CLIENT:
        query = query.filter(Project.client_id == current_user.id)
    
    projects = query.all()
    
    return DashboardStats(
        total=len(projects),
        pending=len([p for p in projects if p.status == ProjectStatus.PENDING]),
        active=len([p for p in projects if p.status == ProjectStatus.IN_PROGRESS]),
        completed=len([p for p in projects if p.status in [ProjectStatus.COMPLETED, ProjectStatus.DELIVERED]])
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific project"""
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
    if current_user.role == UserRole.CLIENT and project.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return project_to_response(project, current_user)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    files: List[UploadFile] = FastAPIFile([]),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new project (Client only)"""
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can create projects"
        )
    
    project_id = generate_id("p-")
    
    # Create project
    project = Project(
        id=project_id,
        workspace_id=current_user.workspace_id,
        client_id=current_user.id,
        title=project_data.title,
        description=project_data.description,
        amount=project_data.amount,
        deadline=project_data.deadline,
        status=ProjectStatus.PENDING,
        payment_status=PaymentStatus.UNPAID
    )
    db.add(project)
    db.flush()
    
    # Save uploaded files
    if files:
        saved_files = await save_multiple_files(files, project_id, "client")
        for file_data in saved_files:
            file_record = ProjectFile(
                id=file_data["id"],
                project_id=project_id,
                file_name=file_data["name"],
                file_path=file_data["path"],
                file_type=file_data["type"],
                file_size=file_data["size"],
                file_category="client",
                uploaded_by=current_user.id
            )
            db.add(file_record)
    
    db.commit()
    db.refresh(project)
    
    return project_to_response(project, current_user)


@router.put("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: str,
    status_update: ProjectStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update project status"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == current_user.workspace_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if current_user.role == UserRole.CLIENT and status_update.status != ProjectStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients can only mark projects as completed"
        )
    
    project.status = status_update.status
    
    # If completed, delete files (remove file records)
    if status_update.status == ProjectStatus.COMPLETED:
        db.query(ProjectFile).filter(ProjectFile.project_id == project_id).delete()
    
    db.commit()
    db.refresh(project)
    
    return project_to_response(project, current_user)


@router.post("/{project_id}/delivery", response_model=ProjectResponse)
async def upload_delivery(
    project_id: str,
    files: List[UploadFile] = FastAPIFile(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload delivery files (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can upload deliveries"
        )
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == current_user.workspace_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Save files
    saved_files = await save_multiple_files(files, project_id, "delivery")
    for file_data in saved_files:
        file_record = ProjectFile(
            id=file_data["id"],
            project_id=project_id,
            file_name=file_data["name"],
            file_path=file_data["path"],
            file_type=file_data["type"],
            file_size=file_data["size"],
            file_category="delivery",
            uploaded_by=current_user.id
        )
        db.add(file_record)
    
    # Update status to delivered
    project.status = ProjectStatus.DELIVERED
    db.commit()
    db.refresh(project)
    
    return project_to_response(project, current_user)


@router.post("/{project_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    project_id: str,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a project"""
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
    if current_user.role == UserRole.CLIENT and project.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    comment = Comment(
        id=generate_id("cm-"),
        project_id=project_id,
        user_id=current_user.id,
        text=comment_data.text
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return CommentResponse(
        id=comment.id,
        userId=comment.user_id,
        userName=current_user.name,
        text=comment.text,
        createdAt=comment.created_at
    )


@router.post("/{project_id}/updates", response_model=ProjectUpdateResponse, status_code=status.HTTP_201_CREATED)
async def add_project_update(
    project_id: str,
    update_data: ProjectUpdateCreate,
    files: List[UploadFile] = FastAPIFile([]),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a project update (Client only)"""
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can add project updates"
        )
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.client_id == current_user.id,
        Project.workspace_id == current_user.workspace_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    update = ProjectUpdate(
        id=generate_id("up-"),
        project_id=project_id,
        text=update_data.text,
        is_read=False
    )
    db.add(update)
    db.flush()
    
    # Save files if any
    if files:
        saved_files = await save_multiple_files(files, project_id, "update")
        for file_data in saved_files:
            file_record = ProjectFile(
                id=file_data["id"],
                project_id=project_id,
                file_name=file_data["name"],
                file_path=file_data["path"],
                file_type=file_data["type"],
                file_size=file_data["size"],
                file_category="update",
                uploaded_by=current_user.id
            )
            db.add(file_record)
    
    db.commit()
    db.refresh(update)
    
    # Get update files
    update_files = [
        FileData(
            id=f.id,
            name=f.file_name,
            url=f"/api/files/{project_id}/update/{f.file_name.split('/')[-1]}",
            type=f.file_type,
            size=f.file_size,
            uploadedAt=f.uploaded_at.isoformat()
        )
        for f in db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.file_category == "update",
            ProjectFile.uploaded_at >= update.created_at
        ).all()
    ]
    
    return ProjectUpdateResponse(
        id=update.id,
        text=update.text,
        files=update_files,
        createdAt=update.created_at,
        isRead=update.is_read
    )


@router.put("/{project_id}/payment/clear", response_model=ProjectResponse)
async def mark_payment_cleared(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark payment as cleared (Client only)"""
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can mark payment as cleared"
        )
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.client_id == current_user.id,
        Project.workspace_id == current_user.workspace_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project.payment_status = PaymentStatus.PENDING_APPROVAL
    db.commit()
    db.refresh(project)
    
    return project_to_response(project, current_user)


@router.put("/{project_id}/payment/approve", response_model=ProjectResponse)
async def approve_payment(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Approve payment (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve payments"
        )
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == current_user.workspace_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project.payment_status = PaymentStatus.PAID
    project.paid_at = datetime.now()
    db.commit()
    db.refresh(project)
    
    return project_to_response(project, current_user)


@router.get("/{project_id}/updates/unread", response_model=List[ProjectUpdateResponse])
async def get_unread_updates(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get unread project updates (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can check for updates"
        )
    
    query = db.query(ProjectUpdate).join(Project).filter(
        Project.workspace_id == current_user.workspace_id,
        ProjectUpdate.is_read == False
    )
    
    if project_id:
        query = query.filter(ProjectUpdate.project_id == project_id)
    
    updates = query.all()
    
    result = []
    for update in updates:
        update_files = [
            FileData(
                id=f.id,
                name=f.file_name,
                url=f"/api/files/{update.project_id}/update/{f.file_name.split('/')[-1]}",
                type=f.file_type,
                size=f.file_size,
                uploadedAt=f.uploaded_at.isoformat()
            )
            for f in db.query(ProjectFile).filter(
                ProjectFile.project_id == update.project_id,
                ProjectFile.file_category == "update",
                ProjectFile.uploaded_at >= update.created_at
            ).all()
        ]
        result.append(ProjectUpdateResponse(
            id=update.id,
            text=update.text,
            files=update_files,
            createdAt=update.created_at,
            isRead=update.is_read
        ))
    
    return result

