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

## 자동 수집 (GitHub Actions - 매일 UTC 14:00 = KST 23:00)

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

## 기술 스택
- Python 3.11, Streamlit, Pandas, Altair
- Playwright (네이버 스크래핑), requests (VOLA API)
- gspread + google-auth (Google Sheets)
- GitHub Actions (스케줄러)
