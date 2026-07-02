# Raw Data

원본 HTML, API 응답, PDF, 이미지 파일을 임시 저장하는 폴더입니다.

## 규칙

- 실제 원본 파일은 Git에 커밋하지 않습니다.
- 파일이 필요한 경우 Supabase Storage, R2, 공유 드라이브 같은 외부 저장소를 사용합니다.
- 이 폴더에는 `.gitkeep`과 이 README만 Git에 남깁니다.

## 예시

```text
data/raw/nongsaro_indoor_catalog/*.html
data/raw/psis_pesticide_safety/*.txt
```
