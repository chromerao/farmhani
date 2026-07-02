from pydantic import BaseModel, Field
from typing import Optional

class UploadSignedUrlRequest(BaseModel):
    fileName: str = Field(..., description="업로드할 파일의 원본 이름 (예: monstera.jpg)")
    mimeType: Optional[str] = Field(None, description="파일의 MIME 타입 (예: image/jpeg)")

class UploadSignedUrlResponse(BaseModel):
    signedUrl: str = Field(..., description="Supabase Storage에 파일을 업로드하기 위한 서명된 URL")
    storagePath: str = Field(..., description="Supabase Storage 내의 상대 저장 경로")
