from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.http import JsonResponse
import json

from ..models import Workspace, User, Project, UserRole
from ..serializers import WorkspaceSerializer


@extend_schema(
    responses={200: WorkspaceSerializer},
    tags=['Workspaces']
)
@api_view(['GET'])
def get_current_workspace(request):
    """Get current user's workspace information"""
    workspace = request.user.workspace
    return Response(WorkspaceSerializer(workspace).data)


@extend_schema(
    responses={200: WorkspaceSerializer},
    tags=['Workspaces']
)
@api_view(['GET'])
def get_workspace(request, workspace_id):
    """Get workspace by ID"""
    try:
        workspace = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        return Response(
            {'detail': 'Workspace not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if workspace.id != request.user.workspace_id:
        return Response(
            {'detail': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    return Response(WorkspaceSerializer(workspace).data)


@extend_schema(
    request=WorkspaceSerializer,
    responses={200: WorkspaceSerializer},
    tags=['Workspaces']
)
@api_view(['PUT'])
def update_workspace(request):
    """Update workspace (Admin only)"""
    if request.user.role != UserRole.ADMIN:
        return Response(
            {'detail': 'Only admins can update workspace'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    workspace = request.user.workspace
    if 'name' in request.data:
        workspace.name = request.data['name']
        workspace.save()
    
    return Response(WorkspaceSerializer(workspace).data)


@extend_schema(
    tags=['Workspaces']
)
@api_view(['GET'])
def get_workspace_stats(request):
    """Get workspace statistics (Admin only)"""
    if request.user.role != UserRole.ADMIN:
        return Response(
            {'detail': 'Only admins can view workspace statistics'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    workspace = request.user.workspace
    total_users = User.objects.filter(workspace=workspace).count()
    total_projects = Project.objects.filter(workspace=workspace).count()
    active_projects = Project.objects.filter(
        workspace=workspace,
        status__in=['pending', 'in_progress', 'delivered']
    ).count()
    
    return Response({
        'workspace_id': workspace.id,
        'workspace_name': workspace.name,
        'workspace_code': workspace.code,
        'total_users': total_users,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'created_at': workspace.created_at.isoformat() if workspace.created_at else None
    })


@extend_schema(
    tags=['Workspaces']
)
@api_view(['GET'])
def export_workspace_data(request):
    """Export complete workspace data (Admin only)"""
    if request.user.role != UserRole.ADMIN:
        return Response(
            {'detail': 'Only admins can export workspace data'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    workspace = request.user.workspace
    users = User.objects.filter(workspace=workspace)
    projects = Project.objects.filter(workspace=workspace)
    
    from datetime import datetime
    from ..models import Comment, ProjectUpdate, ProjectFile
    
    project_ids = [p.id for p in projects]
    comments = Comment.objects.filter(project_id__in=project_ids) if project_ids else []
    updates = ProjectUpdate.objects.filter(project_id__in=project_ids) if project_ids else []
    files = ProjectFile.objects.filter(project_id__in=project_ids) if project_ids else []
    
    export_data = {
        'workspace': {
            'id': str(workspace.id),
            'name': workspace.name,
            'code': workspace.code,
            'owner_id': workspace.owner_id,
            'created_at': workspace.created_at.isoformat() if workspace.created_at else None
        },
        'users': [{
            'id': str(u.id),
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'created_at': u.created_at.isoformat() if u.created_at else None
        } for u in users],
        'projects': [{
            'id': str(p.id),
            'client_id': str(p.client_id),
            'title': p.title,
            'description': p.description,
            'amount': float(p.amount),
            'deadline': p.deadline.isoformat() if p.deadline else None,
            'status': p.status,
            'payment_status': p.payment_status,
            'paid_at': p.paid_at.isoformat() if p.paid_at else None,
            'created_at': p.created_at.isoformat() if p.created_at else None
        } for p in projects],
        'comments': [{
            'id': str(c.id),
            'project_id': str(c.project_id),
            'user_id': str(c.user_id),
            'text': c.text,
            'created_at': c.created_at.isoformat() if c.created_at else None
        } for c in comments],
        'updates': [{
            'id': str(u.id),
            'project_id': str(u.project_id),
            'text': u.text,
            'is_read': u.is_read,
            'created_at': u.created_at.isoformat() if u.created_at else None
        } for u in updates],
        'files': [{
            'id': str(f.id),
            'project_id': str(f.project_id),
            'file_name': f.file_name,
            'file_path': f.file_path,
            'file_type': f.file_type,
            'file_size': f.file_size,
            'file_category': f.file_category,
            'uploaded_by': str(f.uploaded_by_id),
            'uploaded_at': f.uploaded_at.isoformat() if f.uploaded_at else None
        } for f in files],
        'export_date': datetime.now().isoformat(),
        'export_version': '1.0'
    }
    
    return JsonResponse(export_data, json_dumps_params={'indent': 2})

