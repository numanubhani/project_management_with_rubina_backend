from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Workspace, UserRole
from app.schemas import LoginRequest, Token, UserResponse, WorkspaceCreate, WorkspaceResponse
from app.auth import verify_password, get_password_hash, create_access_token
from app.utils import generate_id
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "workspaceId": user.workspace_id,
        "createdAt": user.created_at.isoformat() if user.created_at else datetime.now().isoformat()
    }
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }


@router.post("/register", response_model=Token)
async def register_workspace(workspace_data: WorkspaceCreate, db: Session = Depends(get_db)):
    """Register a new workspace and admin user"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == workspace_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate workspace ID and code
    workspace_id = generate_id("ws-")
    workspace_code = workspace_data.workspace_name.upper()[:6]
    
    # Check if code already exists
    existing_workspace = db.query(Workspace).filter(Workspace.code == workspace_code).first()
    if existing_workspace:
        workspace_code = f"{workspace_code}{generate_id()[:3]}"
    
    # Create workspace
    workspace = Workspace(
        id=workspace_id,
        name=workspace_data.workspace_name,
        code=workspace_code,
        owner_id=workspace_data.email
    )
    db.add(workspace)
    db.flush()
    
    # Create admin user
    user_id = generate_id("admin-")
    user = User(
        id=user_id,
        name=workspace_data.admin_name,
        email=workspace_data.email,
        hashed_password=get_password_hash(workspace_data.password),
        role=UserRole.ADMIN,
        workspace_id=workspace_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "workspaceId": user.workspace_id,
        "createdAt": user.created_at.isoformat() if user.created_at else datetime.now().isoformat()
    }
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }

