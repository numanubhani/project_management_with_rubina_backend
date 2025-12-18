from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from datetime import datetime, timedelta

from ..models import (
    Project, ProjectFile, Comment, ProjectUpdate,
    ProjectStatus, PaymentStatus, UserRole, Collaborator
)
from ..serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectStatusUpdateSerializer,
    CommentSerializer, CommentCreateSerializer,
    ProjectUpdateSerializer, ProjectUpdateCreateSerializer,
    DashboardStatsSerializer, FileDataSerializer, CollaboratorSerializer
)
from ..utils import save_upload_file, generate_id
from ..permissions import IsProjectOwner


def is_project_accessible(user, project):
    """Check if user has access to project (owner, admin, or collaborator)"""
    if user.role == UserRole.ADMIN:
        return True
    if project.client == user:
        return True
    return Collaborator.objects.filter(project=project, user=user).exists()


def delete_files_if_closed(project: Project) -> None:
    """
    Delete all project files only when project is fully closed AND a grace period has passed:
    - Status is COMPLETED
    - Payment status is PAID
    - At least 2 days have passed since payment was marked as paid
    """
    if (
        project.status == ProjectStatus.COMPLETED
        and project.payment_status == PaymentStatus.PAID
        and project.paid_at
    ):
        now = timezone.now()
        if now - project.paid_at >= timedelta(days=2):
            project.files.all().delete()


def project_to_response(project, current_user):
    """Convert Project model to ProjectResponse schema"""
    # Ensure any delayed file deletion rules are applied before building response
    delete_files_if_closed(project)
    # Get files by category (always reflect current DB state; actual deletion is handled in delete_files_if_closed)
    client_files = [
        FileDataSerializer({
            'id': f.id,
            'name': f.file_name,
            'url': f"/api/files/{project.id}/client/{f.file_name.split('/')[-1]}",
            'type': f.file_type,
            'size': f.file_size,
            'uploadedAt': f.uploaded_at.isoformat()
        }).data
        for f in project.files.filter(file_category="client")
    ]
    
    delivery_files = [
        FileDataSerializer({
            'id': f.id,
            'name': f.file_name,
            'url': f"/api/files/{project.id}/delivery/{f.file_name.split('/')[-1]}",
            'type': f.file_type,
            'size': f.file_size,
            'uploadedAt': f.uploaded_at.isoformat()
        }).data
        for f in project.files.filter(file_category="delivery")
    ]

    # Payment proof files (e.g. payment screenshots uploaded by client)
    payment_files = [
        FileDataSerializer({
            'id': f.id,
            'name': f.file_name,
            'url': f"/api/files/{project.id}/payment/{f.file_name.split('/')[-1]}",
            'type': f.file_type,
            'size': f.file_size,
            'uploadedAt': f.uploaded_at.isoformat()
        }).data
        for f in project.files.filter(file_category="payment")
    ]
    
    # Get comments
    comments = CommentSerializer(project.comments.all(), many=True).data
    
    # Get updates (always reflect current DB state)
    updates = []
    for update in project.updates.all():
        base_qs = project.files.filter(
            file_category="update",
            uploaded_at__gte=update.created_at
        )
        update_files = [
            FileDataSerializer({
                'id': f.id,
                'name': f.file_name,
                'url': f"/api/files/{project.id}/update/{f.file_name.split('/')[-1]}",
                'type': f.file_type,
                'size': f.file_size,
                'uploadedAt': f.uploaded_at.isoformat()
            }).data
            for f in base_qs
        ]
        sender_role = None
        first_file = base_qs.first()
        if first_file and hasattr(first_file, "uploaded_by") and first_file.uploaded_by:
            sender_role = first_file.uploaded_by.role

        update_data = ProjectUpdateSerializer(update).data
        update_data['files'] = update_files
        if sender_role:
            update_data['senderRole'] = sender_role
        updates.append(update_data)
    
    # Get collaborators
    collaborators = CollaboratorSerializer(project.collaborators.all(), many=True).data
    
    serializer = ProjectSerializer(project)
    data = serializer.data
    data['clientFiles'] = client_files
    data['deliveryFiles'] = delivery_files
    data['paymentFiles'] = payment_files
    data['comments'] = comments
    data['updates'] = updates
    data['collaborators'] = collaborators
    
    return data


@extend_schema(
    responses={200: ProjectSerializer(many=True)},
    tags=['Projects']
)
@api_view(['GET'])
def get_projects(request):
    """Get all projects for the current user"""
    query = Project.objects.filter(workspace=request.user.workspace)
    
    if request.user.role == UserRole.CLIENT:
        # Get projects where user is client or collaborator
        from django.db.models import Q
        query = query.filter(
            Q(client=request.user) | Q(collaborators__user=request.user)
        ).distinct()
    
    projects = query.order_by('deadline')
    return Response([project_to_response(p, request.user) for p in projects])


@extend_schema(
    responses={200: DashboardStatsSerializer},
    tags=['Projects']
)
@api_view(['GET'])
def get_dashboard_stats(request):
    """Get dashboard statistics"""
    query = Project.objects.filter(workspace=request.user.workspace)
    
    if request.user.role == UserRole.CLIENT:
        query = query.filter(client=request.user)
    
    projects = list(query.all())
    
    return Response({
        'total': len(projects),
        'pending': len([p for p in projects if p.status == ProjectStatus.PENDING]),
        'active': len([p for p in projects if p.status == ProjectStatus.IN_PROGRESS]),
        'completed': len([p for p in projects if p.status in [ProjectStatus.COMPLETED, ProjectStatus.DELIVERED]])
    })


@extend_schema(
    responses={200: ProjectSerializer},
    tags=['Projects']
)
@api_view(['GET'])
def get_project(request, project_id):
    """Get a specific project"""
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check access
    if request.user.role == UserRole.CLIENT and project.client != request.user:
        return Response(
            {'detail': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    return Response(project_to_response(project, request.user))


@extend_schema(
    request=ProjectCreateSerializer,
    responses={201: ProjectSerializer},
    tags=['Projects']
)
@api_view(['POST'])
def create_project(request):
    """Create a new project (Client only)"""
    if request.user.role != UserRole.CLIENT:
        return Response(
            {'detail': 'Only clients can create projects'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProjectCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    project = Project.objects.create(
        workspace=request.user.workspace,
        client=request.user,
        title=serializer.validated_data['title'],
        description=serializer.validated_data['description'],
        amount=serializer.validated_data['amount'],
        deadline=serializer.validated_data['deadline'],
        status=ProjectStatus.PENDING,
        payment_status=PaymentStatus.UNPAID
    )
    
    # Handle file uploads
    files = request.FILES.getlist('files')
    if files:
        for file in files:
            file_data = save_upload_file(file, project.id, "client")
            ProjectFile.objects.create(
                project=project,
                file_name=file_data['name'],
                file_path=file_data['path'],
                file_type=file_data['type'],
                file_size=file_data['size'],
                file_category="client",
                uploaded_by=request.user
            )
    
    return Response(project_to_response(project, request.user), status=status.HTTP_201_CREATED)


@extend_schema(
    request=ProjectStatusUpdateSerializer,
    responses={200: ProjectSerializer},
    tags=['Projects']
)
@api_view(['PUT'])
def update_project_status(request, project_id):
    """Update project status"""
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions - only admins can change project status
    if request.user.role == UserRole.CLIENT:
        return Response(
            {'detail': 'Only admins can change project status'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProjectStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    project.status = serializer.validated_data['status']
    project.save()
    # Delete files only when project is completed AND payment is done
    delete_files_if_closed(project)
    return Response(project_to_response(project, request.user))


@extend_schema(
    responses={200: ProjectSerializer},
    tags=['Projects']
)
@api_view(['POST'])
def upload_delivery(request, project_id):
    """Upload delivery files (Admin only)"""
    if request.user.role != UserRole.ADMIN:
        return Response(
            {'detail': 'Only admins can upload deliveries'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    files = request.FILES.getlist('files')
    if not files:
        return Response(
            {'detail': 'No files provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Save files
    for file in files:
        file_data = save_upload_file(file, project_id, "delivery")
        ProjectFile.objects.create(
            project=project,
            file_name=file_data['name'],
            file_path=file_data['path'],
            file_type=file_data['type'],
            file_size=file_data['size'],
            file_category="delivery",
            uploaded_by=request.user
        )
    
    # Update status to delivered
    project.status = ProjectStatus.DELIVERED
    project.save()
    
    return Response(project_to_response(project, request.user))


@extend_schema(
    request=CommentCreateSerializer,
    responses={201: CommentSerializer},
    tags=['Projects']
)
@api_view(['POST'])
def add_comment(request, project_id):
    """Add a comment to a project"""
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check access (owner, admin, or collaborator)
    if not is_project_accessible(request.user, project):
        return Response(
            {'detail': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CommentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    comment = Comment.objects.create(
        project=project,
        user=request.user,
        text=serializer.validated_data['text']
    )
    
    return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


@extend_schema(
    request=ProjectUpdateCreateSerializer,
    responses={201: ProjectUpdateSerializer},
    tags=['Projects']
)
@api_view(['POST'])
def add_project_update(request, project_id):
    """Add a project update (Client or Admin)"""
    if request.user.role not in [UserRole.CLIENT, UserRole.ADMIN]:
        return Response(
            {'detail': 'Only clients or admins can add project updates'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check access (owner, admin, or collaborator)
    if not is_project_accessible(request.user, project):
        return Response(
            {'detail': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ProjectUpdateCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # If project is delivered and client adds an update, change status back to in_progress
    if request.user.role == UserRole.CLIENT and project.status == ProjectStatus.DELIVERED:
        project.status = ProjectStatus.IN_PROGRESS
        project.save()

    update = ProjectUpdate.objects.create(
        project=project,
        text=serializer.validated_data['text'],
        is_read=False
    )

    # Handle file uploads
    files = request.FILES.getlist('files')
    if files:
        for file in files:
            file_data = save_upload_file(file, project_id, "update")
            ProjectFile.objects.create(
                project=project,
                file_name=file_data['name'],
                file_path=file_data['path'],
                file_type=file_data['type'],
                file_size=file_data['size'],
                file_category="update",
                uploaded_by=request.user
            )

    # Get update files
    update_files = [
        FileDataSerializer({
            'id': f.id,
            'name': f.file_name,
            'url': f"/api/files/{project_id}/update/{f.file_name.split('/')[-1]}",
            'type': f.file_type,
            'size': f.file_size,
            'uploadedAt': f.uploaded_at.isoformat()
        }).data
        for f in project.files.filter(
            file_category="update",
            uploaded_at__gte=update.created_at
        )
    ]

    response_data = ProjectUpdateSerializer(update).data
    response_data['files'] = update_files

    return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema(
    responses={200: ProjectSerializer},
    tags=['Projects']
)
@api_view(['PUT', 'POST'])
def mark_payment_cleared(request, project_id):
    """Mark payment as cleared (Client only)"""
    if request.user.role != UserRole.CLIENT:
        return Response(
            {'detail': 'Only clients can mark payment as cleared'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        project = Project.objects.get(
            id=project_id,
            client=request.user,
            workspace=request.user.workspace
        )
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Store any uploaded payment proof files (screenshots, receipts, etc.)
    files = request.FILES.getlist('files')
    if files:
        for file in files:
            file_data = save_upload_file(file, project_id, "payment")
            ProjectFile.objects.create(
                project=project,
                file_name=file_data['name'],
                file_path=file_data['path'],
                file_type=file_data['type'],
                file_size=file_data['size'],
                file_category="payment",
                uploaded_by=request.user
            )

    project.payment_status = PaymentStatus.PENDING_APPROVAL
    project.save()

    return Response(project_to_response(project, request.user))


@extend_schema(
    responses={200: ProjectSerializer},
    tags=['Projects']
)
@api_view(['PUT'])
def approve_payment(request, project_id):
    """Approve payment (Admin only)"""
    if request.user.role != UserRole.ADMIN:
        return Response(
            {'detail': 'Only admins can approve payments'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        project = Project.objects.get(id=project_id, workspace=request.user.workspace)
    except Project.DoesNotExist:
        return Response(
            {'detail': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    project.payment_status = PaymentStatus.PAID
    project.paid_at = timezone.now()
    project.save()
    # Delete files only when project is completed AND payment is done
    delete_files_if_closed(project)
    return Response(project_to_response(project, request.user))


@extend_schema(
    responses={200: ProjectUpdateSerializer(many=True)},
    tags=['Projects']
)
@api_view(['GET'])
def get_unread_updates(request, project_id=None):
    """Get unread project updates (Admin only)"""
    if request.user.role != UserRole.ADMIN:
        return Response(
            {'detail': 'Only admins can check for updates'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    query = ProjectUpdate.objects.filter(
        project__workspace=request.user.workspace,
        is_read=False
    )
    
    if project_id:
        query = query.filter(project_id=project_id)
    
    updates = query.all()
    
    result = []
    for update in updates:
        base_qs = update.project.files.filter(
            file_category="update",
            uploaded_at__gte=update.created_at
        )
        update_files = [
            FileDataSerializer({
                'id': f.id,
                'name': f.file_name,
                'url': f"/api/files/{update.project.id}/update/{f.file_name.split('/')[-1]}",
                'type': f.file_type,
                'size': f.file_size,
                'uploadedAt': f.uploaded_at.isoformat()
            }).data
            for f in base_qs
        ]
        sender_role = None
        first_file = base_qs.first()
        if first_file and hasattr(first_file, "uploaded_by") and first_file.uploaded_by:
            sender_role = first_file.uploaded_by.role

        update_data = ProjectUpdateSerializer(update).data
        update_data['files'] = update_files
        if sender_role:
            update_data['senderRole'] = sender_role
        result.append(update_data)
    
    return Response(result)

