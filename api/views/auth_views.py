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
    
    # Check if code already exists
    if Workspace.objects.filter(code=workspace_code).exists():
        workspace_code = f"{workspace_code}{generate_id()[:3]}"
    
    # Create workspace
    workspace = Workspace.objects.create(
        id=workspace_id,
        name=serializer.validated_data['workspace_name'],
        code=workspace_code,
        owner_id=email
    )
    
    # Create admin user
    user = User.objects.create_user(
        id=generate_id("admin-"),
        name=serializer.validated_data['admin_name'],
        email=email,
        password=serializer.validated_data['password'],
        role=UserRole.ADMIN,
        workspace=workspace
    )
    
    # Generate token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    user_data = UserSerializer(user).data
    return Response({
        'access_token': access_token,
        'token_type': 'bearer',
        'user': user_data
    }, status=status.HTTP_201_CREATED)

