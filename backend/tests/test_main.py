import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_plants():
    response = client.get("/api/v1/plants")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "몬스테라"

def test_create_plant():
    payload = {
        "name": "홍바오",
        "species": "Ficus elastica",
        "location": "거실 안쪽",
        "sunlight": "반음지"
    }
    response = client.post("/api/v1/plants", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "홍바오"
    assert "id" in data
    assert "createdAt" in data

def test_create_care_log():
    plant_id = "d3b07384-d113-49c3-a558-1ec114a84d41"
    payload = {
        "wateredAt": "2026-06-25",
        "leafCondition": "잎 끝이 약간 노랗게 마름",
        "soilCondition": "손가락 마디 깊이까지 바짝 말라 있음",
        "memo": "최근 물 준지 10일 지남"
    }
    response = client.post(f"/api/v1/plants/{plant_id}/care-logs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["leafCondition"] == "잎 끝이 약간 노랗게 마름"
    assert "id" in data
    assert data["plantId"] == plant_id

def test_create_plant_photo():
    plant_id = "d3b07384-d113-49c3-a558-1ec114a84d41"
    payload = {
        "storagePath": "users/d3b07384/plants/leaf_yellow.jpg",
        "capturedAt": "2026-06-29T12:00:00Z",
        "note": "클로즈업 촬영"
    }
    response = client.post(f"/api/v1/plants/{plant_id}/photos", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["storagePath"] == "users/d3b07384/plants/leaf_yellow.jpg"

def test_consult_plant_care():
    payload = {
        "plantId": "d3b07384-d113-49c3-a558-1ec114a84d41",
        "question": "잎 끝이 노랗게 변하는 이유가 뭘까요?"
    }
    response = client.post("/api/v1/chat/plant-care", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "possibleCauses" in data
    assert "todayActions" in data
    assert len(data["citations"]) > 0
    assert "safetyNotice" in data
