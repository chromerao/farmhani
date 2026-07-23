# Farm하니 Git 협업 규칙

이 문서는 `main`을 안정적인 배포 브랜치로 유지하면서, `develop`을 중심으로 팀별 기능을 안전하게 통합하기 위한 협업 규칙입니다.

## 1. 브랜치 구조

```text
main                              운영 및 최종 배포
└─ develop                        통합 개발
   ├─ feature/backend/login
   ├─ feature/frontend/login-ui
   ├─ feature/data/plant-catalog
   ├─ fix/backend/auth-error
   └─ docs/api-guide
```

### `main`

- 운영에 배포할 수 있는 안정된 코드만 유지합니다.
- 직접 커밋하거나 직접 push하지 않습니다.
- 버전을 출시할 때만 `develop` 또는 `release/*`에서 PR을 생성합니다.
- 병합 후 `v1.0.0`, `v1.1.0`과 같은 Git 태그를 생성합니다.

### `develop`

- 팀 전체 개발 결과를 통합하는 기본 브랜치입니다.
- 일반적인 기능 및 수정 PR의 대상 브랜치는 `develop`입니다.
- 직접 push하지 않고 PR로만 병합합니다.
- 가능한 한 항상 실행 가능한 상태를 유지합니다.

### 작업 브랜치

- 모든 작업 브랜치는 최신 `develop`에서 생성합니다.
- 하나의 브랜치에서는 하나의 기능 또는 수정만 처리합니다.
- 병합이 끝난 작업 브랜치는 원격과 로컬에서 정리합니다.

```bash
git switch develop
git pull origin develop
git switch -c feature/backend/login
```

## 2. 브랜치 이름 규칙

브랜치 이름은 다음 구조를 사용합니다.

```text
<작업종류>/<담당영역>/<작업내용>
```

| 작업 종류 | 용도 | 예시 |
|---|---|---|
| `feature` | 새로운 기능 | `feature/backend/auth` |
| `fix` | 버그 수정 | `fix/frontend/login-error` |
| `refactor` | 기능 변화 없는 구조 개선 | `refactor/backend/rag-pipeline` |
| `test` | 테스트 추가 또는 수정 | `test/backend/auth-api` |
| `docs` | 문서 변경 | `docs/deployment-guide` |
| `chore` | 설정, 의존성 및 기타 작업 | `chore/server/vercel-config` |
| `hotfix` | 운영 긴급 수정 | `hotfix/login-failure` |

담당 영역은 다음 중 하나를 사용합니다.

- `backend`
- `frontend`
- `data`
- `server`

브랜치명은 영문 소문자와 하이픈 사용을 권장합니다.

```text
feature/backend/supabase-auth
feature/frontend/plant-dashboard
feature/data/rag-preprocessing
fix/server/vercel-cors
```

`feat: 로그인 작업` 같은 형식은 브랜치명이 아니라 커밋 메시지에 사용합니다. 브랜치명에는 공백, 따옴표 또는 콜론을 사용하지 않습니다.

## 3. 커밋 메시지 규칙

커밋 메시지는 Conventional Commits 형식을 따릅니다.

```text
<종류>(<담당영역>): <변경 내용>
```

담당 영역이 불필요하면 괄호 부분은 생략할 수 있습니다.

```text
feat(backend): Supabase JWT 검증 추가
fix(frontend): 로그인 요청 URL 수정
feat(data): 식물 카탈로그 전처리 추가
test(backend): 인증 실패 API 테스트 추가
docs: Vercel 배포 방법 추가
chore: Python 의존성 버전 정리
```

커밋 하나에는 가능한 한 하나의 의미 있는 변경만 포함합니다.

## 4. 기본 작업 흐름

### 작업 시작

```bash
git switch develop
git pull origin develop
git switch -c feature/backend/login
```

### 작업 및 push

```bash
git add backend/
git commit -m "feat(backend): Supabase 로그인 검증 추가"
git push -u origin feature/backend/login
```

### PR 생성 전 최신화

PR을 생성하거나 병합하기 전에 최신 `develop`을 작업 브랜치에 반영하고 충돌을 해결합니다.

```bash
git fetch origin
git merge origin/develop
```

충돌 해결 후 관련 테스트를 다시 실행하고 push합니다.

```bash
git push origin feature/backend/login
```

공유된 브랜치에서는 `git push --force` 또는 `git push -f`를 사용하지 않습니다.

### PR 생성 및 병합

일반 작업의 PR 방향은 다음과 같습니다.

```text
feature/backend/login → develop
```

- 리뷰 승인과 CI 통과 후 병합합니다.
- 기능 브랜치는 가급적 `Squash and merge`로 병합해 `develop`의 이력을 간결하게 유지합니다.
- 병합이 끝난 작업 브랜치는 삭제합니다.

## 5. PR 규칙

PR 제목은 커밋 메시지와 동일한 형식을 권장합니다.

```text
feat(backend): Supabase 로그인 검증 추가
fix(frontend): 배포 환경 로그인 오류 수정
```

PR 본문에는 다음 내용을 포함합니다.

```markdown
## 변경 이유
왜 이 작업이 필요한지 설명합니다.

## 주요 변경사항
- 변경사항 1
- 변경사항 2

## 영향 범위
- Backend / Frontend / Data / Server
- API 계약 변경 여부
- DB 변경 여부

## 테스트
- 실행한 테스트
- 수동 확인 결과

## 환경변수
- 추가된 환경변수 없음
또는
- VARIABLE_NAME 추가 필요 — 실제 값은 작성하지 않음

## 참고
관련 이슈, 화면, 문서 또는 주의사항
```

PR 병합 조건은 다음과 같습니다.

- 최소 1명 이상의 리뷰 승인
- CI 및 테스트 통과
- 충돌 없음
- 리뷰 의견 처리 완료
- secret, `.env`, 원본 데이터 및 로그 파일이 포함되지 않았는지 확인
- API 계약 변경 시 프론트엔드와 백엔드 영향 확인

긴급한 상황이 아니라면 본인이 작성한 PR을 혼자 승인하고 병합하지 않습니다.

## 6. 버전 출시 방식

`v1`, `v2`는 개발 브랜치 이름보다 출시 버전과 태그로 관리하는 것을 권장합니다.

출시 직전 안정화가 필요하면 `develop`에서 릴리스 브랜치를 생성합니다.

```bash
git switch develop
git pull origin develop
git switch -c release/v1.0.0
git push -u origin release/v1.0.0
```

`release/v1.0.0`에서는 새로운 기능을 추가하지 않고 다음 작업만 수행합니다.

- 최종 테스트
- 버전 정보 변경
- 문서 정리
- 출시 직전 버그 수정

검증이 끝나면 다음 방향으로 PR을 생성합니다.

```text
release/v1.0.0 → main
```

병합 후 태그를 생성합니다.

```bash
git switch main
git pull origin main
git tag -a v1.0.0 -m "Farm하니 v1.0.0"
git push origin v1.0.0
```

릴리스 브랜치에서 발생한 수정사항은 `develop`에도 반드시 반영합니다.

## 7. 운영 긴급 수정

운영 중 긴급한 문제가 발생하면 `main`에서 `hotfix` 브랜치를 생성합니다.

```bash
git switch main
git pull origin main
git switch -c hotfix/login-failure
```

수정 후 `main`과 `develop` 양쪽에 PR을 생성합니다.

```text
hotfix/login-failure → main
hotfix/login-failure → develop
```

`main`에만 반영하면 다음 출시에서 같은 문제가 다시 발생할 수 있으므로 `develop`에도 반드시 반영합니다.

## 8. 충돌 및 보안 사고 방지

- 작업 브랜치는 가능한 한 짧게 유지합니다.
- 하나의 브랜치에서 여러 기능을 동시에 개발하지 않습니다.
- 공용 파일을 수정하기 전에 팀에 알립니다.
- `README.md`, `.env.example`, API 계약, lock 파일, 배포 설정 변경은 특히 주의합니다.
- 같은 파일을 여러 명이 수정해야 한다면 담당 범위를 먼저 나눕니다.
- 다른 사람의 변경을 삭제하거나 덮어쓰지 않습니다.
- `git reset --hard`와 강제 push를 사용하지 않습니다.
- `.env`, API Key, DB 비밀번호, 개인 토큰 등의 비밀값을 커밋하지 않습니다.
- 원본 대용량 데이터, 사용자 업로드 파일, 모델 weight를 커밋하지 않습니다.

## 9. GitHub 브랜치 보호 권장 설정

### `main`

- Require a pull request before merging
- 최소 1명 승인 필수
- Require status checks to pass
- Require conversation resolution
- Block force pushes
- Block branch deletion
- 직접 push 제한

### `develop`

- Require a pull request before merging
- 최소 1명 승인 권장
- Require status checks to pass
- Block force pushes
- 직접 push 제한

## 10. 전체 흐름 요약

```text
일반 기능:
develop → 작업 브랜치 → PR → develop

버전 출시:
develop → release/v1.0.0 → PR → main → v1.0.0 태그

운영 긴급 수정:
main → hotfix/* → main과 develop 양쪽에 PR
```

핵심 원칙은 다음과 같습니다.

1. `main`과 `develop`에는 직접 push하지 않습니다.
2. 모든 일반 작업은 최신 `develop`에서 브랜치를 생성합니다.
3. 모든 변경은 PR과 리뷰를 거쳐 병합합니다.
4. `feat: 작업 내용`은 커밋 메시지에 사용하고, 브랜치는 `feature/backend/작업명` 형식을 사용합니다.
