from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Farm하니? Plant Care RAG API",
    description="식물 주치의 AI MVP용 FastAPI 서버입니다.",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시 특정 도메인으로 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=200)
async def health_check():
    """
    인프라 및 배포 Health Check를 위한 엔드포인트
    """
    return {
        "status": "healthy",
        "service": "Farm하니? Backend API",
        "version": "0.1.0"
    }

# Mock API 또는 추가 라우터는 여기에 Include 예정
# from app.api.v1 import plants
# app.include_router(plants.router, prefix="/api/v1")
