from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiExample

from ..models import Workspace, UserRole
from ..serializers import (
    LoginSerializer, TokenSerializer, WorkspaceCreateSerializer,
    UserSerializer
)
from ..utils import generate_id

User = get_user_model()


@extend_schema(
    request=LoginSerializer,
    responses={200: TokenSerializer},
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login user"""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    try:
        user = User.objects.get(email=email)
        if not user.check_password(password):
            return Response(
                {'detail': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    except User.DoesNotExist:
        return Response(
            {'detail': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Generate JWT token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    user_data = UserSerializer(user).data
    return Response({
        'access_token': access_token,
        'token_type': 'bearer',
        'user': user_data
    })


@extend_schema(
    request=WorkspaceCreateSerializer,
    responses={200: TokenSerializer},
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_workspace(request):
    """Register a new workspace and admin user"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {'detail': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate workspace ID and code
        workspace_id = generate_id("ws-")
        workspace_code = serializer.validated_data['workspace_name'].upper()[:6]
        
        # Ensure code is valid (remove special characters, limit length)
        workspace_code = ''.join(c for c in workspace_code if c.isalnum())[:6]
        if not workspace_code:
            workspace_code = "WS" + generate_id()[:4]
        
        # Check if code already exists and generate unique one
        max_attempts = 10
        attempt = 0
        while Workspace.objects.filter(code=workspace_code).exists() and attempt < max_attempts:
            workspace_code = f"{workspace_code[:4]}{generate_id()[:2]}"
            attempt += 1
        
        if attempt >= max_attempts:
            workspace_code = "WS" + generate_id()[:8]
        
        # Create workspace with explicit ID
        workspace = Workspace(id=workspace_id)
        workspace.name = serializer.validated_data['workspace_name']
        workspace.code = workspace_code
        workspace.owner_id = email
        workspace.save()
        
        # Create admin user - don't pass id to create_user, let save() handle it
        user_id = generate_id("admin-")
        user = User(
            id=user_id,
            email=email,
            name=serializer.validated_data['admin_name'],
            role=UserRole.ADMIN,
            workspace=workspace
        )
        user.set_password(serializer.validated_data['password'])
        user.save()
        
        # Generate token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        user_data = UserSerializer(user).data
        return Response({
            'access_token': access_token,
            'token_type': 'bearer',
            'user': user_data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return Response(
            {'detail': f'Registration failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

