import secrets
import string
import os
from typing import List
from fastapi import UploadFile
from app.config import settings
from app.schemas import FileData
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    """Generate a random ID"""
    random_string = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(9))
    return f"{prefix}{random_string}" if prefix else random_string


async def save_upload_file(file: UploadFile, project_id: str, category: str) -> dict:
    """Save an uploaded file and return file metadata"""
    # Create directory structure: uploads/{project_id}/{category}/
    file_dir = os.path.join(settings.UPLOAD_DIR, project_id, category)
    os.makedirs(file_dir, exist_ok=True)
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    file_id = generate_id("f-")
    file_name = f"{file_id}{file_ext}"
    file_path = os.path.join(file_dir, file_name)
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Calculate file size
    file_size_bytes = len(content)
    if file_size_bytes < 1024:
        file_size_str = f"{file_size_bytes} B"
    elif file_size_bytes < 1024 * 1024:
        file_size_str = f"{file_size_bytes / 1024:.1f} KB"
    else:
        file_size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
    
    # Return file metadata
    return {
        "id": file_id,
        "name": file.filename,
        "path": file_path,
        "type": file.content_type or "application/octet-stream",
        "size": file_size_str,
        "url": f"/api/files/{project_id}/{category}/{file_name}"
    }


def file_data_to_schema(file_data: dict, file_id: str) -> FileData:
    """Convert file data to FileData schema"""
    return FileData(
        id=file_id,
        name=file_data["name"],
        url=file_data["url"],
        type=file_data["type"],
        size=file_data["size"],
        uploadedAt=datetime.now().isoformat()
    )


async def save_multiple_files(
    files: List[UploadFile],
    project_id: str,
    category: str
) -> List[dict]:
    """Save multiple uploaded files - supports all file types"""
    saved_files = []
    for file in files:
        if file.size and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            continue  # Skip files that are too large
        
        # Accept all file types (images, PDFs, archives, documents, presentations, etc.)
        # No file type restrictions - clients can submit any kind of data
        file_data = await save_upload_file(file, project_id, category)
        saved_files.append(file_data)
    return saved_files

