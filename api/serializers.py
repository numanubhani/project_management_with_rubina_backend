from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    User, Workspace, Project, ProjectFile, Comment, ProjectUpdate,
    UserRole, ProjectStatus, PaymentStatus, Collaborator, CollaboratorInvitation
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    workspaceId = serializers.CharField(source='workspace_id', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'workspaceId', 'createdAt']
        read_only_fields = ['id', 'createdAt']


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'code', 'owner_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class WorkspaceCreateSerializer(serializers.Serializer):
    workspace_name = serializers.CharField()
    admin_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class FileDataSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    url = serializers.CharField()
    type = serializers.CharField()
    size = serializers.CharField()
    uploadedAt = serializers.CharField()


class CommentSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user_id', read_only=True)
    userName = serializers.CharField(source='user.name', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'userId', 'userName', 'text', 'createdAt']
        read_only_fields = ['id', 'userId', 'userName', 'createdAt']


class CommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField()


class ProjectUpdateSerializer(serializers.ModelSerializer):
    files = FileDataSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    isRead = serializers.BooleanField(source='is_read', read_only=True)

    class Meta:
        model = ProjectUpdate
        fields = ['id', 'text', 'files', 'createdAt', 'isRead']
        read_only_fields = ['id', 'files', 'createdAt', 'isRead']


class ProjectUpdateCreateSerializer(serializers.Serializer):
    text = serializers.CharField()


class CollaboratorSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user_id', read_only=True)
    userName = serializers.CharField(source='user.name', read_only=True)
    userEmail = serializers.CharField(source='user.email', read_only=True)
    addedAt = serializers.DateTimeField(source='added_at', read_only=True)

    class Meta:
        model = Collaborator
        fields = ['id', 'userId', 'userName', 'userEmail', 'addedAt']
        read_only_fields = ['id', 'userId', 'userName', 'userEmail', 'addedAt']


class CollaboratorInvitationSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source='project_id', read_only=True)
    projectTitle = serializers.CharField(source='project.title', read_only=True)
    invitedById = serializers.CharField(source='invited_by_id', read_only=True)
    invitedByName = serializers.CharField(source='invited_by.name', read_only=True)
    invitedUserId = serializers.CharField(source='invited_user_id', read_only=True)
    invitedUserName = serializers.CharField(source='invited_user.name', read_only=True)
    invitedUserEmail = serializers.CharField(source='invited_user.email', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    respondedAt = serializers.DateTimeField(source='responded_at', read_only=True, allow_null=True)

    class Meta:
        model = CollaboratorInvitation
        fields = [
            'id', 'projectId', 'projectTitle', 'invitedById', 'invitedByName',
            'invitedUserId', 'invitedUserName', 'invitedUserEmail', 'status',
            'createdAt', 'respondedAt'
        ]
        read_only_fields = [
            'id', 'projectId', 'projectTitle', 'invitedById', 'invitedByName',
            'invitedUserId', 'invitedUserName', 'invitedUserEmail', 'createdAt', 'respondedAt'
        ]


class CollaboratorInvitationCreateSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    
    def validate(self, data):
        if not data.get('user_id') and not data.get('email'):
            raise serializers.ValidationError("Either user_id or email must be provided")
        if data.get('user_id') and data.get('email'):
            raise serializers.ValidationError("Provide either user_id or email, not both")
        return data


class CollaboratorInvitationResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class ProjectSerializer(serializers.ModelSerializer):
    workspaceId = serializers.CharField(source='workspace_id', read_only=True)
    clientId = serializers.CharField(source='client_id', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    paymentStatus = serializers.CharField(source='payment_status', read_only=True)
    paidAt = serializers.DateTimeField(source='paid_at', read_only=True, allow_null=True)
    clientFiles = FileDataSerializer(many=True, read_only=True)
    deliveryFiles = FileDataSerializer(many=True, read_only=True)
    paymentFiles = FileDataSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    updates = ProjectUpdateSerializer(many=True, read_only=True)
    collaborators = CollaboratorSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'workspaceId', 'clientId', 'title', 'description', 'amount',
            'createdAt', 'deadline', 'status', 'paymentStatus', 'paidAt',
            'clientFiles', 'deliveryFiles', 'paymentFiles', 'comments', 'updates',
            'collaborators'
        ]
        read_only_fields = ['id', 'createdAt']


class ProjectCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    amount = serializers.FloatField()
    deadline = serializers.DateTimeField()


class ProjectStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProjectStatus.choices)


class PaymentStatusUpdateSerializer(serializers.Serializer):
    payment_status = serializers.ChoiceField(choices=PaymentStatus.choices)


class DashboardStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    active = serializers.IntegerField()
    completed = serializers.IntegerField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class TokenSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    user = UserSerializer()


class ProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    password = serializers.CharField(required=False, write_only=True)

