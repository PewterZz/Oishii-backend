from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Path
from fastapi.responses import FileResponse
from typing import Optional
from ....services.file_service import save_upload_file, delete_file
from pathlib import Path
from ...v1.endpoints.users import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Define upload directory
UPLOAD_DIR = Path("uploads")

@router.post("/profile-picture", status_code=status.HTTP_201_CREATED)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a profile picture for the current user.
    """
    try:
        file_path = await save_upload_file(file, "profile_pictures")
        
        # In a real app, we would update the user's profile_picture field in the database
        # For now, we'll just return the file path
        
        return {"file_path": file_path}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/food-image", status_code=status.HTTP_201_CREATED)
async def upload_food_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload an image for a food listing.
    """
    try:
        file_path = await save_upload_file(file, "food_images")
        
        # In a real app, we would associate this image with a food listing
        # For now, we'll just return the file path
        
        return {"file_path": file_path}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{file_path:path}", status_code=status.HTTP_200_OK)
async def get_uploaded_file(file_path: str):
    """
    Get an uploaded file by its path.
    """
    full_path = UPLOAD_DIR / file_path
    
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(full_path)

@router.delete("/{file_path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_uploaded_file(
    file_path: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an uploaded file by its path.
    """
    # In a real app, we would verify the user owns this file
    
    success = await delete_file(file_path)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not be deleted"
        )
    
    return None 