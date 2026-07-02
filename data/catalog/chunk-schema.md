# RAG Chunk Schema

`data/scripts/chunk_documents.py`가 생성하는 chunk schema입니다. Backend v0.2.0의 Supabase RAG 테이블 규격에 맞춰 `rag_sources.source_id`는 UUID, `rag_chunks.text`와 `rag_chunks.symptom_keywords`는 top-level 컬럼으로 생성합니다.

## rag_sources

`data/processed/rag_sources.sample.jsonl`

```json
{
  "source_id": "6efea7b7-f610-5885-bf2a-2bdc2455c483",
  "source_key": "nongsaro_indoor_catalog",
  "title": "농사로 실내식물 정보",
  "publisher": "농촌진흥청 농사로",
  "url": "https://www.nongsaro.go.kr/...",
  "license": "verify_required",
  "category": "indoor_care",
  "priority": 1
}
```

Supabase 매핑:

```text
rag_sources.source_id <- source_id
rag_sources.title     <- title
rag_sources.url       <- url
rag_sources.publisher <- publisher
```

## rag_chunks

`data/processed/rag_chunks.sample.jsonl`

```json
{
  "chunk_id": "0fdb3f28-3306-54ad-a760-757679422a36",
  "chunk_key": "nongsaro_indoor_catalog:abc123def0:0001",
  "source_id": "6efea7b7-f610-5885-bf2a-2bdc2455c483",
  "source_key": "nongsaro_indoor_catalog",
  "doc_id": "nongsaro_indoor_catalog:rawhash",
  "title": "농사로 실내식물 정보",
  "publisher": "농촌진흥청 농사로",
  "url": "https://www.nongsaro.go.kr/...",
  "license": "verify_required",
  "collected_at": "2026-06-30T00:00:00+00:00",
  "category": "indoor_care",
  "section": "watering",
  "excerpt": "검색 결과와 출처 패널에 표시할 짧은 발췌문",
  "priority": 1,
  "usage_scope": "rag_and_catalog",
  "crop_or_plant": ["몬스테라"],
  "symptom_keywords": ["leaf_yellowing", "overwatering"],
  "safety_tags": ["not_diagnosis"],
  "text": "검색에 사용할 chunk 본문",
  "metadata": {
    "chunkId": "0fdb3f28-3306-54ad-a760-757679422a36",
    "chunkKey": "nongsaro_indoor_catalog:abc123def0:0001",
    "docId": "nongsaro_indoor_catalog:rawhash",
    "sourceId": "6efea7b7-f610-5885-bf2a-2bdc2455c483",
    "sourceKey": "nongsaro_indoor_catalog",
    "title": "농사로 실내식물 정보",
    "publisher": "농촌진흥청 농사로",
    "url": "https://www.nongsaro.go.kr/...",
    "license": "verify_required",
    "category": "indoor_care",
    "section": "watering",
    "excerpt": "검색 결과와 출처 패널에 표시할 짧은 발췌문",
    "contentPreview": "검색 결과와 출처 패널에 표시할 짧은 발췌문",
    "cropOrPlant": ["몬스테라"],
    "symptomKeywords": ["leaf_yellowing", "overwatering"],
    "safetyTags": ["not_diagnosis"],
    "usageScope": "rag_and_catalog"
  }
}
```

Supabase 매핑:

```text
rag_chunks.chunk_id         <- chunk_id
rag_chunks.source_id        <- source_id
rag_chunks.text             <- text
rag_chunks.embedding        <- embedding
rag_chunks.symptom_keywords <- symptom_keywords
rag_chunks.metadata.section <- section
rag_chunks.metadata.excerpt <- excerpt
```

## 필수 규칙

- 모든 source와 chunk의 `source_id`는 UUID 문자열이어야 합니다.
- 원래 사람이 읽는 출처 id는 `source_key`에 남깁니다.
- 모든 chunk에는 `source_id`, `title`, `publisher`, `url`, `text`, `symptom_keywords`가 있어야 합니다.
- 모든 chunk에는 `section`, `excerpt`, `metadata.section`, `metadata.excerpt`, `metadata.contentPreview`가 있어야 합니다.
- `text`는 사람이 읽을 수 있는 본문이어야 하며, 숫자 표/ID 목록/라벨만 있는 조각은 청킹 단계에서 제외합니다.
- 병해충/농약 관련 chunk는 `expert_check_required` 또는 `pesticide_caution`을 포함해야 합니다.
- `metadata`는 JSONL 내부 추적용으로 유지할 수 있지만, Supabase 기본 적재는 `text`와 `symptom_keywords` 컬럼을 직접 사용합니다.
- `source_key`는 [source_registry.json](source_registry.json)의 id와 일치해야 합니다.
