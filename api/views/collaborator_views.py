from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.utils import timezone

from ..models import (
    Project, Collaborator, CollaboratorInvitation, User, UserRole
)
from ..serializers import (
    CollaboratorSerializer, CollaboratorInvitationSerializer,
    CollaboratorInvitationCreateSerializer, CollaboratorInvitationResponseSerializer
)


def is_project_accessible(user, project):
    """Check if user has access to project (owner, admin, or collaborator)"""
    if user.role == UserRole.ADMIN:
        return True
    if project.client == user:
        return True
    return Collaborator.objects.filter(project=project, user=user).exists()


@extend_schema(
    responses={200: CollaboratorSerializer(many=True)},
    tags=['Collaborators']
)
@api_view(['GET'])
def get_project_collaborators(request, project_id):
    """Get all collaborators for a project"""
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check access
    if not is_project_accessible(request.user, project):
        return Response(
            {'detail': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    collaborators = Collaborator.objects.filter(project=project)
    return Response(CollaboratorSerializer(collaborators, many=True).data)


@extend_schema(
    request=CollaboratorInvitationCreateSerializer,
    responses={201: CollaboratorInvitationSerializer},
    tags=['Collaborators']
)
@api_view(['POST'])
def invite_collaborator(request, project_id):
    """Invite a user to collaborate on a project"""
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Project owner (client) or admin can invite collaborators
    if request.user.role == UserRole.CLIENT and project.client != request.user:
        return Response(
            {'detail': 'Only project owner can invite collaborators'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CollaboratorInvitationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Get user by email or user_id
    invited_user = None
    if serializer.validated_data.get('email'):
        try:
            invited_user = User.objects.get(
                email=serializer.validated_data['email'],
                workspace=request.user.workspace
            )
        except User.DoesNotExist:
            return Response(
                {'detail': 'User with this email not found in workspace'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif serializer.validated_data.get('user_id'):
        try:
            invited_user = User.objects.get(
                id=serializer.validated_data['user_id'],
                workspace=request.user.workspace
            )
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Can't invite yourself
    if invited_user == request.user:
        return Response(
            {'detail': 'Cannot invite yourself'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Can't invite the project owner
    if invited_user == project.client:
        return Response(
            {'detail': 'User is already the project owner'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already a collaborator
    if Collaborator.objects.filter(project=project, user=invited_user).exists():
        return Response(
            {'detail': 'User is already a collaborator'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if there's already a pending invitation
    existing_invitation = CollaboratorInvitation.objects.filter(
        project=project,
        invited_user=invited_user,
        status='pending'
    ).first()
    
    if existing_invitation:
        return Response(
            CollaboratorInvitationSerializer(existing_invitation).data,
            status=status.HTTP_200_OK
        )
    
    # Create new invitation
    invitation = CollaboratorInvitation.objects.create(
        project=project,
        invited_by=request.user,
        invited_user=invited_user,
        status='pending'
    )
    
    return Response(
        CollaboratorInvitationSerializer(invitation).data,
        status=status.HTTP_201_CREATED
    )


@extend_schema(
    request=CollaboratorInvitationResponseSerializer,
    responses={200: CollaboratorInvitationSerializer},
    tags=['Collaborators']
)
@api_view(['POST'])
def respond_to_invitation(request, invitation_id):
    """Accept or reject a collaborator invitation"""
    try:
        invitation = CollaboratorInvitation.objects.get(
            id=invitation_id,
            invited_user=request.user,
            status='pending'
        )
    except CollaboratorInvitation.DoesNotExist:
        return Response(
            {'detail': 'Invitation not found or already responded'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = CollaboratorInvitationResponseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    accept = serializer.validated_data['accept']
    
    if accept:
        # Create collaborator
        Collaborator.objects.get_or_create(
            project=invitation.project,
            user=invitation.invited_user,
            defaults={'invitation': invitation}
        )
        invitation.status = 'accepted'
    else:
        invitation.status = 'rejected'
    
    invitation.responded_at = timezone.now()
    invitation.save()
    
    return Response(CollaboratorInvitationSerializer(invitation).data)


@extend_schema(
    responses={200: CollaboratorInvitationSerializer(many=True)},
    tags=['Collaborators']
)
@api_view(['GET'])
def get_my_invitations(request):
    """Get all pending invitations for the current user"""
    invitations = CollaboratorInvitation.objects.filter(
        invited_user=request.user,
        status='pending'
    ).order_by('-created_at')
    
    return Response(CollaboratorInvitationSerializer(invitations, many=True).data)


@extend_schema(
    responses={204: None},
    tags=['Collaborators']
)
@api_view(['DELETE'])
def remove_collaborator(request, project_id, collaborator_id):
    """Remove a collaborator from a project"""
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only project owner (client) or admin can remove collaborators
    if request.user.role == UserRole.CLIENT and project.client != request.user:
        return Response(
            {'detail': 'Only project owner can remove collaborators'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        collaborator = Collaborator.objects.get(id=collaborator_id, project=project)
    except Collaborator.DoesNotExist:
        return Response(
            {'detail': 'Collaborator not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    collaborator.delete()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

