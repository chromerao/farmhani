import type { Plant, PlantCareChatResponse } from "./types";

export const mockPlants: Plant[] = [
  {
    id: "d3b07384-d113-49c3-a558-1ec114a84d41",
    name: "몬티",
    species: "Monstera deliciosa",
    location: "거실 창가",
    sunlight: "밝은 간접광",
    createdAt: "2026-06-01T12:00:00Z",
    healthScore: 92,
    moisture: "적정",
    nextTask: "내일 오전 흙 수분 확인",
    imageUrl:
      "https://images.unsplash.com/photo-1614594975525-e45190c55d0b?auto=format&fit=crop&w=1200&q=80"
  },
  {
    id: "e4c18495-e224-5aa4-b669-2fd225b95e52",
    name: "상추 텃밭",
    species: "Lactuca sativa",
    location: "베란다 화분",
    sunlight: "오전 직사광선",
    createdAt: "2026-06-10T09:30:00Z",
    healthScore: 78,
    moisture: "건조 주의",
    nextTask: "오늘 저녁 관수",
    imageUrl:
      "https://images.unsplash.com/photo-1622205313162-be1d5712a43d?auto=format&fit=crop&w=1200&q=80"
  },
  {
    id: "mock-ficus",
    name: "홍바오",
    species: "Ficus elastica",
    location: "거실 안쪽",
    sunlight: "반음지",
    createdAt: "2026-06-16T08:00:00Z",
    healthScore: 84,
    moisture: "약간 건조",
    nextTask: "잎 먼지 닦기",
    imageUrl:
      "https://images.unsplash.com/photo-1598880940080-ff9a29891b85?auto=format&fit=crop&w=1200&q=80"
  }
];

export const mockChatResponse: PlantCareChatResponse = {
  summary: "잎 끝 마름과 하엽 황화가 관찰됩니다. 현재는 과습 확정보다 수분 부족, 강한 빛, 통풍 부족 가능성을 함께 점검해야 합니다.",
  possibleCauses: [
    "최근 관수 간격이 길어져 토양 하부 수분이 부족했을 가능성",
    "오후 직사광선에 의한 잎끝 스트레스",
    "환기 부족으로 인한 잎 표면 증산 균형 저하"
  ],
  todayActions: [
    "흙 표면 2~3cm 아래 수분을 손가락으로 확인",
    "흙이 말랐다면 배수구로 물이 빠질 정도로 충분히 관수",
    "오후 직사광선은 피하고 창가에서 40~60cm 안쪽으로 이동",
    "노랗게 마른 하엽은 깨끗한 가위로 제거"
  ],
  observationChecklist: [
    "새 잎까지 노랗게 변하는지",
    "줄기 밑동이 물러지거나 냄새가 나는지",
    "잎 뒷면에 해충 흔적이 있는지"
  ],
  citations: [
    {
      sourceId: "nongsaro_indoor_water",
      title: "농사로 실내식물 물관리 자료",
      publisher: "농촌진흥청/농사로",
      url: "https://www.nongsaro.go.kr/"
    },
    {
      sourceId: "nihhs_indoor_garden",
      title: "실내정원 유지관리 자료",
      publisher: "국립원예특작과학원"
    }
  ],
  safetyNotice: "이 결과는 공식 자료 기반 관리 가이드이며 병해충 확정 진단이 아닙니다. 증상이 악화되면 전문가 확인이 필요합니다."
};
