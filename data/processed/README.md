# Processed Data

Backend 적재 직전의 정제 산출물을 저장하는 폴더입니다.

## 규칙

- 실제 산출물은 기본적으로 Git에 커밋하지 않습니다.
- PR 리뷰용으로 아주 작은 sample을 올려야 할 경우, 팀장 승인 후 `.gitignore` 예외를 먼저 조정합니다.

## 예시

```text
data/processed/plant_master.sample.jsonl
data/processed/rag_sources.sample.jsonl
data/processed/rag_chunks.sample.jsonl
data/processed/symptom_reference.sample.jsonl
data/processed/image_manifest.sample.csv
```
