import os
import shutil
from fastapi import UploadFile, HTTPException, status
from typing import List
import uuid
from pathlib import Path
import aiofiles
from ..core.supabase import supabase

# Define upload directory
UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def save_upload_file(upload_file: UploadFile, folder: str) -> str:
    """
    Save an uploaded file to the specified folder.
    Returns the file path relative to the upload directory.
    """
    # Validate file size
    file_size = 0
    contents = await upload_file.read(MAX_FILE_SIZE + 1)
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )
    
    # Validate file extension
    file_ext = upload_file.filename.split(".")[-1].lower() if "." in upload_file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{file_ext}' not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Create directory if it doesn't exist
    upload_folder = UPLOAD_DIR / folder
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    # Generate a unique filename
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = upload_folder / unique_filename
    
    # Write the file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Return the relative path
    return str(Path(folder) / unique_filename)

async def upload_to_supabase(file: UploadFile, bucket: str, path: str) -> str:
    """
    Upload a file to Supabase Storage.
    
    Args:
        file: The file to upload
        bucket: The storage bucket name
        path: The file path within the bucket
        
    Returns:
        The public URL of the uploaded file
    """
    # Validate file size
    file_size = 0
    contents = await file.read(MAX_FILE_SIZE + 1)
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )
    
    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{file_ext}' not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Create a temporary file
    temp_file = Path(f"/tmp/{uuid.uuid4()}.{file_ext}")
    async with aiofiles.open(temp_file, "wb") as f:
        await f.write(contents)
    
    try:
        # Upload to Supabase Storage
        with open(temp_file, "rb") as f:
            response = supabase.storage.from_(bucket).upload(path, f, {"content-type": f"image/{file_ext}"})
        
        # Get the public URL
        file_url = supabase.storage.from_(bucket).get_public_url(path)
        
        return file_url
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to Supabase Storage: {str(e)}"
        )
    finally:
        # Clean up the temporary file
        if temp_file.exists():
            os.remove(temp_file)

async def delete_file(file_path: str) -> bool:
    """
    Delete a file from the upload directory.
    Returns True if successful, False otherwise.
    """
    full_path = UPLOAD_DIR / file_path
    
    if not full_path.exists():
        return False
    
    try:
        os.remove(full_path)
        return True
    except Exception:
        return False 