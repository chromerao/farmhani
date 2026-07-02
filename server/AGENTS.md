# Server Agent 지침

## 작업 범위

- 수정 가능: `server/`, `.env.example`
- 읽기 권장: `docs/deployment.md`, `docs/architecture.md`
- 수정 전 합의 필요: `frontend/`, `backend/`, `data/`

## 책임

- Dockerfile / Docker Compose
- Render/Railway/Fly.io 배포 설정
- Vercel frontend 배포 가이드 지원
- 환경변수 관리
- health check와 로그 확인 절차
- CI/CD와 rollback 문서

## 보안 규칙

- secret을 Dockerfile, compose, deploy script에 하드코딩하지 않습니다.
- 운영 secret은 배포 서비스 secret manager에만 등록합니다.
- local/staging/production 환경을 분리합니다.
- service role key 접근자는 최소화합니다.

## 운영 체크

- `/health`가 DB와 vector store 상태를 확인하는지 검토합니다.
- 배포 후 로그인, 식물 등록, AI 상담 샘플 요청을 smoke test로 확인합니다.
- 장애 시 rollback 방법과 로그 위치를 README에 남깁니다.
