import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.auth.security import get_current_user
from app.db.session import get_supabase_client
from app.core.config import settings
from app.schemas.upload import UploadSignedUrlRequest, UploadSignedUrlResponse

router = APIRouter(prefix="/uploads", tags=["Uploads"])

@router.post("/signed-url", response_model=UploadSignedUrlResponse, status_code=status.HTTP_200_OK, summary="사진 업로드용 signed URL 발급")
async def create_signed_upload_url(
    request: UploadSignedUrlRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    Supabase Storage 사진 업로드용 signed URL을 발급합니다.
    격리된 사용자 경로: users/{user_id}/plants/{uuid}_{filename}
    """
    try:
        # 파일 확장자 및 고유 파일명 생성
        _, ext = os.path.splitext(request.fileName)
        unique_filename = f"{uuid.uuid4()}{ext}"
        storage_path = f"users/{current_user_id}/plants/{unique_filename}"
        
        # Supabase Storage Signed Upload URL 발급
        bucket_name = settings.SUPABASE_STORAGE_BUCKET
        response = db.storage.from_(bucket_name).create_signed_upload_url(storage_path)
        
        signed_url = response.get("signedUrl") or response.get("signed_url")
        if not signed_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Signed URL 생성에 실패했습니다."
            )
            
        return UploadSignedUrlResponse(
            signedUrl=signed_url,
            storagePath=storage_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signed URL 발급 중 오류가 발생했습니다: {str(e)}"
        )
