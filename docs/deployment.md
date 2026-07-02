# Deployment

## 추천 조합

| 파트 | 추천 서비스 | 이유 |
|---|---|---|
| Frontend | Vercel | Next.js/React 프리뷰 배포, GitHub PR 연동, 환경변수 관리가 쉽습니다. |
| Backend API | Render 또는 Railway | FastAPI 상시 서버, background worker, Docker 배포를 MVP에서 빠르게 운영할 수 있습니다. |
| Advanced Backend | Fly.io | 지역 배포와 Docker 제어가 필요할 때 적합합니다. 초반에는 복잡할 수 있습니다. |
| Auth/DB/Vector | Supabase | 로그인/로그아웃, Postgres, pgvector, Storage를 한 번에 제공합니다. |
| Object Storage | Supabase Storage 또는 Cloudflare R2 | 사용자 사진과 공식 문서 원본을 Git 밖에 저장합니다. |
| DNS/CDN | Cloudflare | 도메인, DNS, HTTPS, 캐시, R2 확장에 좋습니다. |

## 환경 분리

- Local: 각자 `.env`를 사용하고 Git에 올리지 않습니다.
- Staging: PR 또는 develop 브랜치 배포. 테스트용 Supabase project 사용을 권장합니다.
- Production: 발표/시연용 안정 환경. service role key 접근자를 최소화합니다.

## 배포 책임

- Frontend 담당: Vercel project, public env, API URL, auth redirect URL.
- Backend 담당: FastAPI 실행 명령, health check endpoint, migration 실행.
- Server 담당: Dockerfile/compose, Render/Railway/Fly 배포 설정, secret 등록, rollback 문서.
- 팀장: 배포 URL, 도메인, 발표용 계정, 최종 smoke test.

## Health check 기준

- Frontend: `/` 접속 가능, 로그인 버튼 렌더링, API URL 환경변수 확인.
- Backend: `/health` 200 응답, DB 연결 확인, vector store 연결 확인.
- Auth: 로그인, 로그아웃, refresh session 동작.
- RAG: 샘플 질문에서 근거 문서가 포함된 답변 반환.

## 피해야 할 배포 방식

- Backend/RAG를 프론트 서버리스 함수에 모두 넣는 방식은 피합니다. 이미지 업로드, RAG 검색, LangGraph 실행 시간이 길어질 수 있습니다.
- SQLite/local Chroma만 사용하는 운영 배포는 피합니다. 팀원 환경과 배포 환경에서 데이터가 달라집니다.
- 원본 AI Hub 데이터나 사용자 사진을 repo에 넣고 배포하지 않습니다.
