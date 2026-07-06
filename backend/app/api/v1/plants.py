import logging
import uuid
from datetime import datetime, date, timezone
from typing import List
from fastapi import APIRouter, Path, status, Depends, HTTPException
from app.schemas.plant import Plant, PlantCreate, PlantPhoto, PlantPhotoCreate, PlantDetail, PlantUpdate, WateringReminder
from app.schemas.care_log import CareLog, CareLogCreate, CareLogUpdate
from app.auth.security import get_current_user
from app.db.session import get_supabase_client
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plants", tags=["Plants"])

@router.get("", response_model=List[Plant], summary="사용자의 식물 목록 조회")
def list_plants(
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    현재 로그인한 사용자의 모든 식물 프로필 목록을 데이터베이스에서 조회하여 반환합니다.
    """
    try:
        response = db.table("plants").select("*").eq("user_id", str(current_user_id)).execute()
        
        plants = []
        for item in response.data:
            plants.append(Plant(
                id=uuid.UUID(item["id"]),
                name=item["name"],
                species=item.get("species"),
                location=item.get("location"),
                sunlight=item.get("sunlight"),
                imageUrl=item.get("image_url"),
                createdAt=datetime.fromisoformat(item["created_at"])
            ))
        return plants
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="식물 목록 조회 중 오류가 발생했습니다."
        )

# 종별 기본 물주기 간격이 정해지기 전까지 사용하는 공통 권장 간격
DEFAULT_WATERING_INTERVAL_DAYS = 7

# 주의: 이 라우트는 GET /plants/{plantId} 보다 먼저 선언되어야 한다 (경로 매칭 우선순위)
@router.get("/reminders", response_model=List[WateringReminder], summary="물주기 리마인더 조회")
def list_watering_reminders(
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    사용자의 모든 식물에 대해 마지막 물 준 날짜(care_logs.watered_at) 기준으로
    물주기 도래 여부를 계산해 반환합니다.
    """
    try:
        plants_res = db.table("plants").select("id,name,species").eq("user_id", str(current_user_id)).execute()
        plants = plants_res.data or []
        if not plants:
            return []

        plant_ids = [item["id"] for item in plants]
        logs_res = (
            db.table("care_logs")
            .select("plant_id,watered_at")
            .in_("plant_id", plant_ids)
            .not_.is_("watered_at", "null")
            .order("watered_at", desc=True)
            .execute()
        )
        last_watered: dict[str, str] = {}
        for log in logs_res.data or []:
            pid = log["plant_id"]
            if pid not in last_watered:
                last_watered[pid] = log["watered_at"]

        today = datetime.now(timezone.utc).date()
        reminders = []
        for item in plants:
            watered_raw = last_watered.get(item["id"])
            days_since = None
            reminder_status = "unknown"
            if watered_raw:
                watered_date = date.fromisoformat(str(watered_raw)[:10])
                days_since = (today - watered_date).days
                remaining = DEFAULT_WATERING_INTERVAL_DAYS - days_since
                if remaining <= 0:
                    reminder_status = "due"
                elif remaining <= 1:
                    reminder_status = "upcoming"
                else:
                    reminder_status = "ok"
            reminders.append(WateringReminder(
                plantId=uuid.UUID(item["id"]),
                name=item["name"],
                species=item.get("species"),
                lastWateredAt=str(watered_raw)[:10] if watered_raw else None,
                daysSinceWatered=days_since,
                intervalDays=DEFAULT_WATERING_INTERVAL_DAYS,
                status=reminder_status
            ))
        # 물이 급한 순서로 정렬 (due → upcoming → unknown → ok)
        order = {"due": 0, "upcoming": 1, "unknown": 2, "ok": 3}
        reminders.sort(key=lambda r: (order.get(r.status, 9), -(r.daysSinceWatered or 0)))
        return reminders
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="물주기 리마인더 조회 중 오류가 발생했습니다."
        )

@router.post("", response_model=Plant, status_code=status.HTTP_201_CREATED, summary="식물 프로필 신규 등록")
def create_plant(
    plant_in: PlantCreate,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    새로운 식물 프로필을 데이터베이스에 등록합니다.
    """
    try:
        insert_data = {
            "user_id": str(current_user_id),
            "name": plant_in.name,
            "species": plant_in.species,
            "location": plant_in.location,
            "sunlight": plant_in.sunlight,
            "image_url": plant_in.imageUrl
        }
        response = db.table("plants").insert(insert_data).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="식물 등록에 실패했습니다."
            )
        
        item = response.data[0]
        return Plant(
            id=uuid.UUID(item["id"]),
            name=item["name"],
            species=item.get("species"),
            location=item.get("location"),
            sunlight=item.get("sunlight"),
            imageUrl=item.get("image_url"),
            createdAt=datetime.fromisoformat(item["created_at"])
        )
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="식물 등록 중 오류가 발생했습니다."
        )

@router.post("/{plantId}/care-logs", response_model=CareLog, status_code=status.HTTP_201_CREATED, summary="식물 재배/물주기 로그 등록")
def create_care_log(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    log_in: CareLogCreate = ...,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    특정 식물에 대한 물주기, 상태 점검 및 메모를 포함한 재배 일지 로그를 등록합니다.
    """
    try:
        # 식물이 존재하고 현재 사용자가 소유하고 있는지 확인
        plant_check = db.table("plants").select("id").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )
            
        insert_data = {
            "plant_id": str(plantId),
            "watered_at": log_in.wateredAt.isoformat() if log_in.wateredAt else None,
            "leaf_condition": log_in.leafCondition,
            "soil_condition": log_in.soilCondition,
            "memo": log_in.memo
        }
        
        response = db.table("care_logs").insert(insert_data).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="재배 로그 등록에 실패했습니다."
            )
            
        item = response.data[0]
        return CareLog(
            id=uuid.UUID(item["id"]),
            plantId=uuid.UUID(item["plant_id"]),
            wateredAt=date.fromisoformat(item["watered_at"]) if item.get("watered_at") else None,
            leafCondition=item.get("leaf_condition"),
            soilCondition=item.get("soil_condition"),
            memo=item.get("memo"),
            createdAt=datetime.fromisoformat(item["created_at"])
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재배 로그 등록 중 오류가 발생했습니다."
        )

@router.post("/{plantId}/photos", response_model=PlantPhoto, status_code=status.HTTP_201_CREATED, summary="식물 사진 메타데이터 등록")
def create_plant_photo(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    photo_in: PlantPhotoCreate = ...,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    Supabase Storage 등에 업로드 완료된 식물 사진의 경로 및 메타데이터를 백엔드에 등록합니다.
    """
    try:
        # 식물이 존재하고 현재 사용자가 소유하고 있는지 확인
        plant_check = db.table("plants").select("id").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )
            
        insert_data = {
            "plant_id": str(plantId),
            "storage_path": photo_in.storagePath,
            "note": photo_in.note,
            "captured_at": photo_in.capturedAt.isoformat() if photo_in.capturedAt else datetime.now(timezone.utc).isoformat()
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
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="식물 사진 등록 중 오류가 발생했습니다."
        )

@router.get("/{plantId}", response_model=PlantDetail, summary="식물 상세 프로필 조회")
def get_plant_detail(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    특정 식물의 정보, 재배 로그 히스토리 및 사진 목록을 함께 조회하여 반환합니다.
    """
    try:
        plant_response = db.table("plants").select("*").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )
        plant_data = plant_response.data[0]
        
        logs_response = db.table("care_logs").select("*").eq("plant_id", str(plantId)).order("created_at", desc=True).execute()
        photos_response = db.table("plant_photos").select("*").eq("plant_id", str(plantId)).order("created_at", desc=True).execute()
        
        care_logs = []
        for item in logs_response.data:
            care_logs.append(CareLog(
                id=uuid.UUID(item["id"]),
                plantId=uuid.UUID(item["plant_id"]),
                wateredAt=date.fromisoformat(item["watered_at"]) if item.get("watered_at") else None,
                leafCondition=item.get("leaf_condition"),
                soilCondition=item.get("soil_condition"),
                memo=item.get("memo"),
                createdAt=datetime.fromisoformat(item["created_at"])
            ))
            
        photos = []
        for item in photos_response.data:
            photos.append(PlantPhoto(
                id=uuid.UUID(item["id"]),
                plantId=uuid.UUID(item["plant_id"]),
                storagePath=item["storage_path"],
                capturedAt=datetime.fromisoformat(item["captured_at"]),
                note=item.get("note"),
                createdAt=datetime.fromisoformat(item["created_at"])
            ))
            
        return PlantDetail(
            id=uuid.UUID(plant_data["id"]),
            name=plant_data["name"],
            species=plant_data.get("species"),
            location=plant_data.get("location"),
            sunlight=plant_data.get("sunlight"),
            imageUrl=plant_data.get("image_url"),
            createdAt=datetime.fromisoformat(plant_data["created_at"]),
            careLogs=care_logs,
            photos=photos
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="식물 상세 조회 중 오류가 발생했습니다."
        )

@router.delete("/{plantId}", status_code=status.HTTP_204_NO_CONTENT, summary="식물 프로필 삭제")
def delete_plant(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    특정 식물 프로필을 삭제합니다. 관련 로그와 사진도 Cascade 설정에 의해 자동 삭제됩니다.
    """
    try:
        plant_check = db.table("plants").select("id").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )
            
        db.table("plants").delete().eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        return
    except HTTPException:
        raise
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="식물 삭제 중 오류가 발생했습니다."
        )

@router.patch("/{plantId}", response_model=Plant, summary="식물 프로필 수정")
def update_plant(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    plant_in: PlantUpdate = ...,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    try:
        plant_check = db.table("plants").select("id").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )
            
        update_data = {}
        if plant_in.name is not None:
            update_data["name"] = plant_in.name
        if plant_in.species is not None:
            update_data["species"] = plant_in.species
        if plant_in.location is not None:
            update_data["location"] = plant_in.location
        if plant_in.sunlight is not None:
            update_data["sunlight"] = plant_in.sunlight
        if plant_in.imageUrl is not None:
            update_data["image_url"] = plant_in.imageUrl
            
        if not update_data:
            plant_res = db.table("plants").select("*").eq("id", str(plantId)).execute()
            item = plant_res.data[0]
        else:
            response = db.table("plants").update(update_data).eq("id", str(plantId)).execute()
            item = response.data[0]
            
        return Plant(
            id=uuid.UUID(item["id"]),
            name=item["name"],
            species=item.get("species"),
            location=item.get("location"),
            sunlight=item.get("sunlight"),
            imageUrl=item.get("image_url"),
            createdAt=datetime.fromisoformat(item["created_at"])
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="식물 프로필 수정 중 오류가 발생했습니다."
        )

@router.put("/{plantId}/care-logs/{logId}", response_model=CareLog, summary="재배 로그 수정")
def update_care_log(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    logId: uuid.UUID = Path(..., description="로그 UUID"),
    log_in: CareLogUpdate = ...,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    try:
        plant_check = db.table("plants").select("id").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )
        log_check = db.table("care_logs").select("id").eq("id", str(logId)).eq("plant_id", str(plantId)).execute()
        if not log_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 식물의 재배 로그를 찾을 수 없습니다."
            )
            
        update_data = {}
        if log_in.wateredAt is not None:
            update_data["watered_at"] = log_in.wateredAt.isoformat()
        if log_in.leafCondition is not None:
            update_data["leaf_condition"] = log_in.leafCondition
        if log_in.soilCondition is not None:
            update_data["soil_condition"] = log_in.soilCondition
        if log_in.memo is not None:
            update_data["memo"] = log_in.memo
            
        if not update_data:
            item = log_check.data[0]
        else:
            response = db.table("care_logs").update(update_data).eq("id", str(logId)).execute()
            item = response.data[0]
            
        return CareLog(
            id=uuid.UUID(item["id"]),
            plantId=uuid.UUID(item["plant_id"]),
            wateredAt=date.fromisoformat(item["watered_at"]) if item.get("watered_at") else None,
            leafCondition=item.get("leaf_condition"),
            soilCondition=item.get("soil_condition"),
            memo=item.get("memo"),
            createdAt=datetime.fromisoformat(item["created_at"])
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재배 로그 수정 중 오류가 발생했습니다."
        )

@router.delete("/{plantId}/care-logs/{logId}", status_code=status.HTTP_204_NO_CONTENT, summary="재배 로그 삭제")
def delete_care_log(
    plantId: uuid.UUID = Path(..., description="식물 UUID"),
    logId: uuid.UUID = Path(..., description="로그 UUID"),
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    try:
        plant_check = db.table("plants").select("id").eq("id", str(plantId)).eq("user_id", str(current_user_id)).execute()
        if not plant_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="식물을 찾을 수 없거나 해당 식물에 대한 권한이 없습니다."
            )
        log_check = db.table("care_logs").select("id").eq("id", str(logId)).eq("plant_id", str(plantId)).execute()
        if not log_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 식물의 재배 로그를 찾을 수 없습니다."
            )
            
        db.table("care_logs").delete().eq("id", str(logId)).execute()
        return
    except HTTPException:
        raise
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재배 로그 삭제 중 오류가 발생했습니다."
        )

