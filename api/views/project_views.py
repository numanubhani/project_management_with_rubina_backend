from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from datetime import datetime

from ..models import (
    Project, ProjectFile, Comment, ProjectUpdate,
    ProjectStatus, PaymentStatus, UserRole
)
from ..serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectStatusUpdateSerializer,
    CommentSerializer, CommentCreateSerializer,
    ProjectUpdateSerializer, ProjectUpdateCreateSerializer,
    DashboardStatsSerializer, FileDataSerializer
)
from ..utils import save_upload_file, generate_id
from ..permissions import IsProjectOwner


def project_to_response(project, current_user):
    """Convert Project model to ProjectResponse schema"""
    # Get files by category
    client_files = []
    delivery_files = []
    
    if project.status != ProjectStatus.COMPLETED:
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
    
    # Get comments
    comments = CommentSerializer(project.comments.all(), many=True).data
    
    # Get updates
    updates = []
    for update in project.updates.all():
        update_files = []
        if project.status != ProjectStatus.COMPLETED:
            update_files = [
                FileDataSerializer({
                    'id': f.id,
                    'name': f.file_name,
                    'url': f"/api/files/{project.id}/update/{f.file_name.split('/')[-1]}",
                    'type': f.file_type,
                    'size': f.file_size,
                    'uploadedAt': f.uploaded_at.isoformat()
                }).data
                for f in project.files.filter(
                    file_category="update",
                    uploaded_at__gte=update.created_at
                )
            ]
        updates.append({
            **ProjectUpdateSerializer(update).data,
            'files': update_files
        })
    
    serializer = ProjectSerializer(project)
    data = serializer.data
    data['clientFiles'] = client_files
    data['deliveryFiles'] = delivery_files
    data['comments'] = comments
    data['updates'] = updates
    
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
        query = query.filter(client=request.user)
    
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
    
    # If completed, delete files (remove file records)
    if project.status == ProjectStatus.COMPLETED:
        project.files.all().delete()
    
    project.save()
    
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
    
    # Check access
    if request.user.role == UserRole.CLIENT and project.client != request.user:
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
    """Add a project update (Client only)"""
    if request.user.role != UserRole.CLIENT:
        return Response(
            {'detail': 'Only clients can add project updates'},
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
    
    serializer = ProjectUpdateCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # If project is delivered and client adds an update, change status back to in_progress
    if project.status == ProjectStatus.DELIVERED:
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
@api_view(['PUT'])
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
        update_files = [
            FileDataSerializer({
                'id': f.id,
                'name': f.file_name,
                'url': f"/api/files/{update.project.id}/update/{f.file_name.split('/')[-1]}",
                'type': f.file_type,
                'size': f.file_size,
                'uploadedAt': f.uploaded_at.isoformat()
            }).data
            for f in update.project.files.filter(
                file_category="update",
                uploaded_at__gte=update.created_at
            )
        ]
        update_data = ProjectUpdateSerializer(update).data
        update_data['files'] = update_files
        result.append(update_data)
    
    return Response(result)

