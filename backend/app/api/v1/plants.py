import uuid
from datetime import datetime, date, timezone
from typing import List
from fastapi import APIRouter, Path, status
from app.schemas.plant import Plant, PlantCreate, PlantPhoto, PlantPhotoCreate
from app.schemas.care_log import CareLog, CareLogCreate

router = APIRouter(prefix="/plants", tags=["Plants"])

# Mock 데이터 저장소 역할 (간단한 메모리 리스트)
MOCK_PLANTS = [
    Plant(
        id=uuid.UUID("d3b07384-d113-49c3-a558-1ec114a84d41"),
        name="몬스테라",
        species="Monstera deliciosa",
        location="거실 창가",
        sunlight="간접광",
        createdAt=datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    ),
    Plant(
        id=uuid.UUID("e4c18495-e224-5aa4-b669-2fd225b95e52"),
        name="상추 텃밭",
        species="Lactuca sativa",
        location="베란다 화분",
        sunlight="오전 직사광선",
        createdAt=datetime(2026, 6, 10, 9, 30, 0, tzinfo=timezone.utc)
    )
]

@router.get("", response_model=List[Plant], summary="사용자의 식물 목록 조회")
async def list_plants():
    """
    현재 로그인한 사용자의 모든 식물 프로필 목록을 반환합니다. (Mock 데이터)
    """
    return MOCK_PLANTS

@router.post("", response_model=Plant, status_code=status.HTTP_201_CREATED, summary="식물 프로필 신규 등록")
async def create_plant(plant_in: PlantCreate):
    """
    새로운 식물 프로필을 등록합니다. (Mock 데이터)
    """
    new_plant = Plant(
        id=uuid.uuid4(),
        name=plant_in.name,
        species=plant_in.species,
        location=plant_in.location,
        sunlight=plant_in.sunlight,
        createdAt=datetime.now(timezone.utc)
    )
    # Mock 리스트에 임시 저장
    MOCK_PLANTS.append(new_plant)
    return new_plant

@router.post("/{plantId}/care-logs", response_model=CareLog, status_code=status.HTTP_201_CREATED, summary="식물 재배/물주기 로그 등록")
async def create_care_log(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    log_in: CareLogCreate = ...
):
    """
    특정 식물에 대한 물주기, 상태 점검 및 메모를 포함한 재배 일지 로그를 등록합니다. (Mock 데이터)
    """
    return CareLog(
        id=uuid.uuid4(),
        plantId=plantId,
        wateredAt=log_in.wateredAt or date.today(),
        leafCondition=log_in.leafCondition or "건강함",
        soilCondition=log_in.soilCondition or "적당히 촉촉함",
        memo=log_in.memo or "로그 없음",
        createdAt=datetime.now(timezone.utc)
    )

@router.post("/{plantId}/photos", response_model=PlantPhoto, status_code=status.HTTP_201_CREATED, summary="식물 사진 메타데이터 등록")
async def create_plant_photo(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    photo_in: PlantPhotoCreate = ...
):
    """
    Supabase Storage 등에 업로드 완료된 식물 사진의 경로 및 메타데이터를 백엔드에 등록합니다. (Mock 데이터)
    """
    return PlantPhoto(
        id=uuid.uuid4(),
        plantId=plantId,
        storagePath=photo_in.storagePath,
        capturedAt=photo_in.capturedAt or datetime.now(timezone.utc),
        note=photo_in.note or "사진 메모 없음",
        createdAt=datetime.now(timezone.utc)
    )
