import secrets
import string
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    """Generate a random ID"""
    random_string = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(9))
    return f"{prefix}{random_string}" if prefix else random_string


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def save_upload_file(file, project_id, category):
    """Save an uploaded file and return file metadata"""
    # Create directory structure: uploads/{project_id}/{category}/
    file_dir = os.path.join(settings.UPLOAD_DIR, project_id, category)
    os.makedirs(file_dir, exist_ok=True)
    
    # Generate unique filename
    file_ext = os.path.splitext(file.name)[1]
    file_id = generate_id("f-")
    file_name = f"{file_id}{file_ext}"
    file_path = os.path.join(file_dir, file_name)
    
    # Save file
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    # Calculate file size
    file_size_bytes = file.size
    file_size_str = format_file_size(file_size_bytes)
    
    # Return file metadata
    return {
        "id": file_id,
        "name": file.name,
        "path": file_path,
        "type": file.content_type or "application/octet-stream",
        "size": file_size_str,
        "url": f"/api/files/{project_id}/{category}/{file_name}"
    }

