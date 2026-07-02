# Vectorstore

embedding 포함 파일 또는 local vector DB 캐시를 임시 저장하는 폴더입니다.

## 규칙

- embedding 포함 파일은 Git에 커밋하지 않습니다.
- 운영 저장소는 Supabase Postgres + pgvector를 기준으로 합니다.

## 예시

```text
data/vectorstore/rag_chunks.embedded.jsonl
```
