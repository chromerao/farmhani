import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from supabase import Client

from app.auth.security import get_current_user
from app.db.session import get_supabase_client, get_supabase_service_client
from app.core.config import settings
from app.schemas.plant import PlantPhoto
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

@router.post("/plant-photo", response_model=PlantPhoto, status_code=status.HTTP_201_CREATED, summary="식물 사진 파일 업로드 및 메타데이터 등록")
async def upload_plant_photo(
    plantId: uuid.UUID = Form(..., description="사진을 연결할 식물 UUID"),
    note: str | None = Form(None, description="사진 메모"),
    capturedAt: str | None = Form(None, description="촬영 시간 ISO 문자열"),
    file: UploadFile = File(..., description="업로드할 식물 사진 파일"),
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    브라우저가 Supabase signed upload URL을 직접 사용할 수 없는 환경을 위한 서버 경유 업로드 API입니다.
    업로드 전 식물 소유권을 검증하고, Storage 저장 후 plant_photos 메타데이터를 등록합니다.
    """
    try:
        plant_check = db.table("plants").select("id").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )

        _, ext = os.path.splitext(file.filename or "")
        safe_ext = ext if ext.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"
        storage_path = f"users/{current_user_id}/plants/{plantId}/{uuid.uuid4()}{safe_ext}"
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드할 사진 파일이 비어 있습니다."
            )

        service_db = get_supabase_service_client()
        service_db.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            storage_path,
            content,
            file_options={
                "content-type": file.content_type or "application/octet-stream",
                "upsert": "false"
            }
        )

        captured_at = datetime.now(timezone.utc)
        if capturedAt:
            captured_at = datetime.fromisoformat(capturedAt.replace("Z", "+00:00"))

        insert_data = {
            "plant_id": str(plantId),
            "storage_path": storage_path,
            "note": note,
            "captured_at": captured_at.isoformat()
        }
        response = db.table("plant_photos").insert(insert_data).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="식물 사진 메타데이터 등록에 실패했습니다."
            )

        item = response.data[0]
        return PlantPhoto(
            id=uuid.UUID(item["id"]),
            plantId=uuid.UUID(item["plant_id"]),
            storagePath=item["storage_path"],
            capturedAt=datetime.fromisoformat(item["captured_at"]),
            note=item.get("note"),
            createdAt=datetime.fromisoformat(item["created_at"])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"식물 사진 업로드 중 오류가 발생했습니다: {str(e)}"
        )
