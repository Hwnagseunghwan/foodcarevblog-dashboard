# foodcarevblog-dashboard 프로젝트

## 개요
- **목적**: Cle 공식블로그(네이버 nature_food) 조회수 + VOLA 단축URL 클릭수 + Google Sheets 업무데이터 수집 → Streamlit 멀티페이지 대시보드
- **GitHub**: https://github.com/Hwnagseunghwan/foodcarevblog-dashboard
- **로컬 경로**: `C:/foodcarevblog-dashboard/`
- **실행**: `streamlit run dashboard.py` 또는 `대시보드실행.bat`

---

## 멀티페이지 구성

| 파일 | 사이드바 명칭 | 설명 |
|---|---|---|
| `dashboard.py` | 📊 Cle Blog Dashboard | 네이버 블로그 조회수 (월별/주간/일간/시사점) |
| `pages/vola_dashboard.py` | 🔗 Vola Dashboard | VOLA 단축URL 클릭수 |
| `pages/work_dashboard.py` | 📋 Work Dashboard | Google Sheets 업무 데이터 |

사이드바: 자동 생성 nav CSS로 숨기고 `st.sidebar.page_link`로 커스텀 구성

---

## 주요 파일

| 파일 | 역할 |
|---|---|
| `naver_scraper.py` | 블로그 일별 조회수 수집 (Playwright) |
| `vola_scraper.py` | VOLA 누적 클릭수 스냅샷 수집 → 전일 차분으로 일별 계산 |
| `sheets_scraper.py` | Google Sheets 공식블_업무시트 수집 |
| `blog_visitors.json` | 블로그 일별 조회수 |
| `blog_visitors_monthly.json` | 블로그 월별 조회수 |
| `vola_clicks.json` | VOLA 클릭수 (snapshots + daily 구조) |
| `work_data.json` | Google Sheets 업무 데이터 |
| `vola_title.xlsx` | VOLA 링크 타이틀 수동 관리 파일 (API 타이틀 깨짐 이슈) |

---

## 자동 수집 (GitHub Actions - 매일 UTC 15:10 = KST 00:10)

```yaml
# .github/workflows/scraper.yml 수집 순서
1. naver_scraper.py   (NAVER_ID, NAVER_PW, BLOG_ID, NAVER_COOKIES)
2. vola_scraper.py    (VOLA_API_KEY)
3. sheets_scraper.py  (GOOGLE_CREDENTIALS)
```

### GitHub Secrets
- `NAVER_ID`, `NAVER_PW`, `BLOG_ID`, `NAVER_COOKIES`
- `VOLA_API_KEY`: db61b33a1da4e7738ddc3064f2a4bb4d
- `GOOGLE_CREDENTIALS`: 서비스 계정 JSON (base64 아님, JSON 그대로)

---

## Cle Blog Dashboard (dashboard.py)

### 탭 구성
1. 📆 월별 추이 (최근 6개월)
2. 📅 주간 현황 (최근 90일, ISO 주차 기준)
3. 📋 일간 현황 (최근 14일, 토🔵 일/공휴🔴)
4. 💡 시사점 (완료된 기간만 분석, 종합→월별→주간→일간)

---

## VOLA Dashboard (pages/vola_dashboard.py)

### 탭 구성
1. 🔗 링크별 현황 (기간 선택, 카테고리 필터, 바 차트 + 숫자)
2. 📋 일별 현황 (최근 14일, 일별 총 클릭 + 카테고리 스택)
3. 📊 전체 데이터

### 카테고리 분류 (longurl 기반)
- `/event/eventDetail/` → 이벤트
- `/shop/mealPlan/E/` → 식단플랜(E)
- `/shop/mealPlan/U/` → 식단플랜(U)
- `/shop/goodsView/` → 상품
- 그 외 → 기타

### VOLA 타이틀 이슈
- API가 모든 링크에 사이트 기본 타이틀(깨진 문자)을 반환함
- `vola_title.xlsx`로 수동 관리 (링크, 타이틀 컬럼)
- `vola_scraper.py`: 기존 저장 타이틀 우선, 깨진 API 타이틀로 덮어쓰지 않음
- 대시보드: 타이틀 없으면 longurl 기반 레이블 자동 생성 (예: 이벤트 #654)

---

## Work Dashboard (pages/work_dashboard.py)

### 탭 구성
```python
tab1, tab2, tab5, tab3, tab4 = st.tabs(["📊 현황 요약", "📨 원고 송출량", "🔑 키워드 노출량", "🔍 원고 목록", "💰 비용 분석"])
```

### 핵심 전처리
```python
# date: "12. 18" 형식 + year 컬럼 → parsed_date
def parse_date(row):
    raw = str(row["date"]).replace(" ", "").replace(".", "-").strip("-")
    year = int(row["year"]) if row["year"] else datetime.now().year
    parts = raw.split("-")
    if len(parts) == 2:
        return pd.Timestamp(f"{year}-{int(parts[0]):02d}-{int(parts[1]):02d}")
    return pd.NaT

# code 기준 중복제거 = 원고 송출 단위
df_dedup = df.drop_duplicates(subset=["code"])[dedup_cols].copy()

# 노출 판단값
EXPOSED_VAL = ["O", "o", "Y", "y", "노출", "True", "TRUE", "1", "1.0"]

# 키워드 노출량 탭: code가 "#VALUE!" 또는 빈값인 행 제외
_code_str = df_kw["code"].astype(str).str.strip()
df_kw = df_kw[~_code_str.isin(["", "nan", "None", "코드없음", "#VALUE!"])]
```

### 필터 위치
- 원고 송출량 탭: 필터(작성자/브랜드/단위) 최상단 → 이후 지표/차트 반영
- 키워드 노출량 탭: 필터(브랜드/제품/노출여부/단위) 최상단 → 이후 지표/차트 반영

### 키워드 노출량 탭 상단 지표 (필터 적용 후)
총 키워드 수 | 총 검색량(M) 합계 | 노출 키워드 수 | 노출 검색량(M) 합계 | 키워드 노출률

### 키워드 노출량 차트 방식
- 막대(브랜드별 스택): 전체 키워드수 / 전체 검색량(M)
- 주황색 라인 오버레이: 노출 키워드수 / 노출 검색량(M)
- 월별(6개월) / 주간별(90일) / 일별(14일)

---

## Google Sheets 연동
- SPREADSHEET_ID: `1fyqDmq8lZG9GyaoSco7rFGCTxXnITTCVb-KQ-XBFKww`
- SHEET_NAME: `공식블_업무시트`
- 인증: `GOOGLE_CREDENTIALS` 환경변수 또는 `google_credentials.json` 파일

---

## 네이버 쿠키 갱신 (트리거: "네이버 쿠키교체")
"네이버 쿠키교체"라고 하면 Claude가 아래 순서를 직접 실행:
1. `PYTHONIOENCODING=utf-8 python C:/Claude_code/get_cookies.py` 실행
2. 사용자가 브라우저에서 네이버 로그인 → 자동 감지 → `nature_food_cookies.json` 저장
3. `nature_food_cookies.json` → `naver_cookies.json` 복사
4. `naver_scraper.py` 실행으로 수집 테스트
5. 변경된 파일 커밋 & 푸시
6. `gh secret set NAVER_COOKIES --repo Hwnagseunghwan/foodcarevblog-dashboard --body "$(cat C:/Claude_code/nature_food_cookies.json)"` 실행

### get_cookies.py 동작 방식 (2026-03-18 수정)
- 기존: `input()` 대기 → Claude Code 환경에서 EOFError 발생
- 수정: 최대 120초간 1초 간격으로 `page.url` 폴링 → `nidlogin` 벗어나면 로그인 완료 감지
- 저장 위치: `C:/Claude_code/nature_food_cookies.json`

### naver_scraper.py 버그 수정 내용 (2026-03-18)
- **문제**: `is_logged_in()`이 `naver.com`만 체크 → admin 세션 만료를 못 감지 → `fetch_stat_api`가 빈 dict 반환하며 조용히 실패
- **수정 1**: `is_logged_in()` → `admin.blog.naver.com/stat/today` 접근 후 URL에 `nidlogin` 포함 여부로 판단
- **수정 2**: `fetch_stat_api()` → 페이지 이동 후 `nidlogin` 감지 시 즉시 반환 + 경고 출력
- **수정 3**: `login()` → `NAVER_ID`/`NAVER_PW` 미설정 시 해결방법 포함한 명확한 예외 발생

### 로컬 .env 자동 로그인 설정 (2026-03-19)
- `C:/foodcarevblog-dashboard/.env` 생성 (gitignore 적용 중)
- NAVER_ID / NAVER_PW 포함 → 쿠키 만료 시 자동 재로그인 후 쿠키 재저장
- 앞으로 로컬 실행 시 수동 쿠키교체 불필요

---

## GitHub Actions 안정화 (2026-03-19)

### continue-on-error 추가
- **문제**: 하나의 스크래퍼가 실패하면 이후 모든 스크래퍼가 실행되지 않음
- **수정**: 모든 스크래퍼 step에 `continue-on-error: true` 추가
- naver_scraper 실패 → vola_scraper, sheets_scraper 등은 계속 실행됨

---

## VOLA Dashboard 일별 현황 시작일 (2026-03-19)
- `pages/vola_dashboard.py` 기본 시작일 `"2026-03-18"` 고정 (기존: 최근 14일 자동 계산)
- 해당 날짜 데이터 없어도 오류 없이 이후 날짜부터 표시
- 하단 시작일 선택기로 사용자 변경 가능

---

## Seeding Dashboard 버그 수정 (2026-03-19)

### 일별 차트 시계열 정렬 오류 수정 (`pages/seeding_dashboard.py`)
- **문제**: Altair `x=alt.X("date:N", sort=None)` → 날짜가 시계열 순서로 정렬되지 않음
- **수정**: `_d_sort = sorted(grp["date"].unique().tolist())` 명시적 정렬 리스트 적용
- 원고 송출량 일별 / 키워드 노출량 일별 차트 모두 적용

### Seeding 스크래퍼 year 보정 로직 추가 (`seeding_scraper.py`)
- **문제**: 스프레드시트 year 컬럼에 2027~2029 미래 연도 잘못 입력 → `max_date`가 미래가 되어 일별 14일 cutoff 계산이 깨짐 → 실제 데이터 전부 차트에서 제외됨
- **수정**: `fix_year()` 함수 추가 — 현재 연도(datetime.now().year) 초과 시 자동 보정
- 매일 수집 시 자동 적용됨

### Seeding Vola Tracker 데이터 수집 누락
- 원인: naver_scraper 실패 → Actions 전체 중단 (continue-on-error로 해결)
- 수동 수집으로 최신 데이터 반영

---

## 배포 (Streamlit Community Cloud)
- **URL**: https://foodcarevblog-dashboard.streamlit.app (GitHub 연동 자동 배포)
- **GitHub**: https://github.com/Hwnagseunghwan/foodcarevblog-dashboard
- **메인 파일**: `dashboard.py`
- **Secrets 관리**: Streamlit Cloud > App settings > Secrets (`.streamlit/secrets.toml` 형식)

---

## 로그인 시스템 (auth.py — Supabase Auth)
- **인증 방식**: Supabase 이메일/비밀번호 로그인
- **Supabase URL**: `https://nowapqtqyhtfkzkkvqei.supabase.co`
- `auth.py`에 URL·ANON_KEY 하드코딩 (secrets 폴백 이슈로)
- `require_login()`: 미로그인 시 로그인 폼 표시 후 `st.stop()`
- `show_user_sidebar()`: 사이드바 하단 이메일 + 로그아웃 버튼
- 전체 5개 페이지 모두 `require_login()` 적용
- 계정 없을 시 관리자에게 Supabase 초대 요청

---

## 멀티페이지 전체 구성 (최신)

| 파일 | 사이드바 명칭 | 설명 |
|---|---|---|
| `dashboard.py` | 📊 Cle Blog Views | 네이버 블로그 조회수 |
| `pages/overview_dashboard.py` | 📈 통합 성과 대시보드 | 블로그+VOLA+원고+비용 KPI |
| `pages/vola_dashboard.py` | 🔗 Vola Dashboard | VOLA 단축URL 클릭수 |
| `pages/work_dashboard.py` | 📋 Work Dashboard | Google Sheets 업무데이터 |
| `pages/seeding_dashboard.py` | 📋 Cle Seeding Work Tracker | 시딩 업무데이터 |
| `pages/seeding_vola_dashboard.py` | 🔗 Cle Seeding Vola Tracker | 시딩 VOLA 클릭수 |

---

## 통합 성과 대시보드 (pages/overview_dashboard.py)
- 블로그 조회수 + VOLA 클릭수 + 원고 발행수 + 마케팅 비용 통합 KPI
- 탭: 월별 / 주별 / 일별
- 블로그 vs 시딩 기여도 파이차트
- 마케팅 퍼널 효율 지표 (전환율, 클릭당 비용 등)
- 자동 시사점 생성
- 기간 선택기 포함
- 사이드바 하단 전체 데이터 재수집 버튼 (경고 문구 포함)

---

## 기술 스택
- Python 3.11, Streamlit, Pandas, Altair
- Playwright (네이버 스크래핑), requests (VOLA API)
- gspread + google-auth (Google Sheets)
- supabase (로그인 인증)
- GitHub Actions (스케줄러) + Streamlit Community Cloud (배포)
