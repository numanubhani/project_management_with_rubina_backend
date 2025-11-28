from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import User, UserRole
from app.schemas import UserCreate, UserResponse
from app.auth import get_current_active_user, get_password_hash
from app.utils import generate_id

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/")
async def get_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all users in the current user's workspace"""
    users = db.query(User).filter(User.workspace_id == current_user.workspace_id).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, 'value') else u.role,
            "workspaceId": u.workspace_id,
            "createdAt": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users"
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    from datetime import datetime
    user_id = generate_id("u-")
    new_user = User(
        id=user_id,
        name=user_data.name,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        workspace_id=current_user.workspace_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role.value if hasattr(new_user.role, 'value') else new_user.role,
        "workspaceId": new_user.workspace_id,
        "createdAt": new_user.created_at.isoformat() if new_user.created_at else datetime.now().isoformat()
    }


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    from datetime import datetime
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
        "workspaceId": current_user.workspace_id,
        "createdAt": current_user.created_at.isoformat() if current_user.created_at else datetime.now().isoformat()
    }


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None

@router.put("/me")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    from datetime import datetime
    if profile_data.name:
        current_user.name = profile_data.name
    if profile_data.password:
        from app.auth import get_password_hash
        current_user.hashed_password = get_password_hash(profile_data.password)
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
        "workspaceId": current_user.workspace_id,
        "createdAt": current_user.created_at.isoformat() if current_user.created_at else datetime.now().isoformat()
    }

