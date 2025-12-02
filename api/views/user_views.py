from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from ..models import User, UserRole
from ..serializers import UserSerializer, ProfileUpdateSerializer
from ..permissions import IsAdmin


@extend_schema(
    responses={200: UserSerializer(many=True)},
    tags=['Users']
)
@api_view(['GET'])
def get_users(request):
    """Get all users in the current user's workspace"""
    users = User.objects.filter(workspace=request.user.workspace)
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@extend_schema(
    request=UserSerializer,
    responses={201: UserSerializer},
    tags=['Users']
)
@api_view(['POST'])
def create_user(request):
    """Create a new user (Admin only)"""
    if request.user.role != UserRole.ADMIN:
        return Response(
            {'detail': 'Only admins can create users'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if email already exists
    if User.objects.filter(email=request.data.get('email')).exists():
        return Response(
            {'detail': 'User with this email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.create_user(
        name=request.data.get('name'),
        email=request.data.get('email'),
        password=request.data.get('password', ''),
        role=request.data.get('role', UserRole.CLIENT),
        workspace=request.user.workspace
    )
    
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(
    responses={200: UserSerializer},
    tags=['Users']
)
@api_view(['GET'])
def get_current_user_info(request):
    """Get current user information"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    request=ProfileUpdateSerializer,
    responses={200: UserSerializer},
    tags=['Users']
)
@api_view(['PUT'])
def update_profile(request):
    """Update current user profile"""
    serializer = ProfileUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    if 'name' in serializer.validated_data:
        request.user.name = serializer.validated_data['name']
    if 'password' in serializer.validated_data:
        request.user.set_password(serializer.validated_data['password'])
    
    request.user.save()
    
    return Response(UserSerializer(request.user).data)

