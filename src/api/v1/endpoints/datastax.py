from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from ....services.langflow_service import refresh_auth_token

router = APIRouter(tags=["datastax"])

@router.post("/refresh-token", response_model=Dict[str, Any])
async def refresh_datastax_token():
    """
    Refresh the DataStax authentication token.
    
    Returns:
        A new valid authentication token with expiry information
    """
    try:
        # Call the token refresh function
        new_token = await refresh_auth_token()
        
        if not new_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh DataStax token. No refresh token available."
            )
        
        # Return the new token with a default expiry time (1 hour)
        return {
            "token": new_token,
            "expires_in": 3600  # 1 hour in seconds
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing DataStax token: {str(e)}"
        ) 