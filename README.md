# 광고를 잘 아는 사람들 — 백엔드 API

## 배포 순서

### 1단계: Supabase 프로젝트 생성
1. https://supabase.com → New Project 생성
2. 프로젝트명: `adpeople` (자유)
3. 비밀번호 설정, Region: Northeast Asia (Tokyo)
4. 생성 후 **SQL Editor** 열기
5. `supabase_schema.sql` 전체 내용 붙여넣기 → **Run** 클릭
6. Settings → API → 아래 두 값 복사:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGci...`

### 2단계: Railway 배포
1. https://railway.app → New Project → Deploy from GitHub (또는 CLI)
2. GitHub에 이 폴더 push하거나, Railway CLI로 직접 배포
3. **Variables** 탭에서 환경변수 설정:

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
PROXY_HOST=kr.decodo.com
PROXY_USER=spuqtp2czv
PROXY_PASS=1voaShrNj_2f4V3hgB
PROXY_PORT_START=10001
PROXY_PORT_END=19999
PORT=8080
```

4. Deploy 클릭 → 자동 빌드
5. Settings → Generate Domain → 도메인 발급 (예: `adpeople-api.up.railway.app`)

### 3단계: 프론트엔드 연동
Netlify에 배포된 index.html에서 API 주소를 Railway 도메인으로 설정

## API 엔드포인트

| 기능 | Method | URL |
|------|--------|-----|
| 헬스체크 | GET | `/health` |
| 프록시 상태 | GET | `/api/proxy/status` |
| KeyHunter 분석 | POST | `/api/keyhunter/analyze` |
| 순위 조회 | POST | `/api/rank/check` |
| 순위 이력 | GET | `/api/rank/history?keyword=시흥+하수구막힘` |
| 매출 조회 | GET | `/api/sales?month=2026-02` |
| 매출 저장 | POST | `/api/sales` |
| 캠페인 목록 | GET | `/api/campaigns` |
| 영업DB 추출 | GET | `/api/sellerdb/search?keyword=인천+맛집` |
| 팀원 목록 | GET | `/api/team` |
| 공지사항 | GET | `/api/notices` |

## 파일 구조
```
adpeople-backend/
├── main.py               ← FastAPI 서버 (전체 API)
├── requirements.txt      ← Python 패키지
├── Dockerfile            ← Railway 빌드용
├── railway.toml          ← Railway 설정
├── supabase_schema.sql   ← DB 테이블 (Supabase에서 실행)
├── .env.example          ← 환경변수 예시
└── README.md             ← 이 파일
```
