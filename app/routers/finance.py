from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from app.database import get_db
from app.models import Project, User, ProjectStatus, PaymentStatus, UserRole
from app.auth import get_current_active_user
from app.routers.projects import project_to_response

router = APIRouter(prefix="/api/finance", tags=["Finance"])


@router.get("/history")
async def get_finance_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get financial history (completed/paid projects)"""
    query = db.query(Project).filter(
        Project.workspace_id == current_user.workspace_id
    )
    
    if current_user.role == UserRole.CLIENT:
        query = query.filter(Project.client_id == current_user.id)
    
    # Filter for completed or paid projects
    projects = query.filter(
        (Project.status == ProjectStatus.COMPLETED) | 
        (Project.payment_status != PaymentStatus.UNPAID)
    ).all()
    
    return [project_to_response(p, current_user) for p in projects]


@router.get("/stats")
async def get_finance_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get financial statistics"""
    query = db.query(Project).filter(
        Project.workspace_id == current_user.workspace_id
    )
    
    if current_user.role == UserRole.CLIENT:
        query = query.filter(Project.client_id == current_user.id)
    
    # Filter for completed or paid projects
    projects = query.filter(
        (Project.status == ProjectStatus.COMPLETED) | 
        (Project.payment_status != PaymentStatus.UNPAID)
    ).all()
    
    total_amount = sum(p.amount for p in projects if p.payment_status == PaymentStatus.PAID)
    pending_amount = sum(
        p.amount for p in projects 
        if p.payment_status == PaymentStatus.PENDING_APPROVAL or 
        (p.status == ProjectStatus.COMPLETED and p.payment_status == PaymentStatus.UNPAID)
    )
    
    return {
        "total_amount": total_amount,
        "pending_amount": pending_amount,
        "projects_count": len(projects)
    }

