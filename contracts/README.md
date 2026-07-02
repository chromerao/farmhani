# Contracts

프론트와 백엔드가 공유하는 계약을 보관합니다.

- `api/openapi.yaml`: HTTP API 계약
- `schemas/`: 필요 시 공통 JSON schema, event schema, DB-view schema

계약 변경은 프론트와 백엔드 양쪽에 영향을 주므로 PR 설명에 breaking change 여부를 적습니다.
