from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Path, Query
from fastapi.responses import FileResponse, RedirectResponse
from typing import Optional, List
from ....services.file_service import save_upload_file, delete_file, upload_to_supabase
from pathlib import Path
from ...v1.endpoints.users import get_current_user
from ....core.supabase import execute_query, execute_raw_sql
import uuid
import os
from pydantic import UUID4

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
    
    The image will be stored in Supabase Storage and the user's profile will be updated
    with the URL of the uploaded image.
    """
    try:
        # Generate a unique filename
        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        unique_filename = f"profile_{current_user['id']}_{uuid.uuid4()}.{file_ext}"
        
        # Upload to Supabase Storage
        file_url = await upload_to_supabase(
            file=file,
            bucket="profile_pictures",
            path=unique_filename
        )
        
        # Update the user's profile_picture field in the database
        await execute_query(
            table="users",
            query_type="update",
            data={"profile_picture": file_url},
            filters={"id": current_user["id"]}
        )
        
        return {
            "message": "Profile picture uploaded successfully",
            "file_url": file_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/food-image", status_code=status.HTTP_201_CREATED)
async def upload_food_image(
    file: UploadFile = File(...),
    food_id: Optional[UUID4] = Query(None, description="Food ID to associate the image with"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload an image for a food listing.
    
    The image will be stored in Supabase Storage. If a food_id is provided,
    the food listing will be updated with the URL of the uploaded image.
    """
    try:
        # Generate a unique filename
        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        unique_filename = f"food_{uuid.uuid4()}.{file_ext}"
        
        # Upload to Supabase Storage
        file_url = await upload_to_supabase(
            file=file,
            bucket="food_images",
            path=unique_filename
        )
        
        # If food_id is provided, update the food listing
        if food_id:
            # Check if the food belongs to the current user
            food_result = await execute_query(
                table="foods",
                query_type="select",
                filters={"id": str(food_id), "user_id": current_user["id"]}
            )
            
            if not food_result or len(food_result) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Food not found or you don't have permission to update it"
                )
            
            # Get the current images
            current_images = food_result[0].get("images", []) if food_result[0].get("images") else []
            
            # Add the new image URL
            updated_images = current_images + [file_url]
            
            # Update the food listing
            await execute_query(
                table="foods",
                query_type="update",
                data={"images": updated_images},
                filters={"id": str(food_id)}
            )
        
        return {
            "message": "Food image uploaded successfully",
            "file_url": file_url,
            "food_id": food_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{file_path:path}", status_code=status.HTTP_200_OK)
async def get_uploaded_file(file_path: str):
    """
    Get an uploaded file by its path.
    
    This endpoint is for backward compatibility. New uploads use Supabase Storage.
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
    
    This endpoint is for backward compatibility. New uploads use Supabase Storage.
    """
    # In a real app, we would verify the user owns this file
    
    success = await delete_file(file_path)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not be deleted"
        )
    
    return None 