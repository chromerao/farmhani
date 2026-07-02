# Server / Infra

로컬 실행, 배포, 환경변수, 운영 설정을 관리하는 영역입니다.

## 권장 배포 구조

- Frontend: Vercel
- Backend API: Render 또는 Railway
- Database/Auth/Vector: Supabase
- Object Storage: Supabase Storage 또는 Cloudflare R2
- DNS/CDN: Cloudflare

## 예정 구조

```text
server/
├── docker/     # Dockerfile, compose override, local service 정의
├── deploy/     # Render/Railway/Fly 설정과 배포 runbook
└── nginx/      # 필요 시 reverse proxy 설정
```

## 환경변수 관리

- 공통 템플릿은 root `.env.example`에만 둡니다.
- 실제 `.env`는 각자 로컬에만 보관합니다.
- Vercel에는 `NEXT_PUBLIC_*` 값만 등록합니다.
- Backend 배포 서비스에는 DB URL, Supabase service role key, LLM key를 등록합니다.

## 배포 순서

1. Supabase project 생성
2. Auth redirect URL 설정
3. Postgres/pgvector 준비
4. Backend staging 배포
5. Frontend staging 배포
6. 로그인/로그아웃 smoke test
7. 식물 등록, 사진 업로드, RAG 상담 smoke test
8. production 환경변수 분리 후 최종 배포
