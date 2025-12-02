from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import FileResponse, Http404
from drf_spectacular.utils import extend_schema
import os

from ..models import Project, ProjectFile, UserRole


@extend_schema(
    tags=['Files']
)
@api_view(['GET'])
def download_file(request, project_id, category, filename):
    """Download a project file"""
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
    
    # Validate category
    if category not in ["client", "delivery", "update"]:
        return Response(
            {'detail': 'Invalid file category'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Find file
    try:
        file_record = ProjectFile.objects.get(
            project_id=project_id,
            file_category=category,
            file_name__contains=filename
        )
    except ProjectFile.DoesNotExist:
        return Response(
            {'detail': 'File not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if file exists on disk
    if not os.path.exists(file_record.file_path):
        return Response(
            {'detail': 'File not found on server'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return FileResponse(
        open(file_record.file_path, 'rb'),
        filename=file_record.file_name,
        content_type=file_record.file_type
    )

