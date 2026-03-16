# Cle 공식블로그 조회수 대시보드 프로젝트

## 프로젝트 개요
- **목적**: 네이버 블로그(nature_food) 조회수를 자동 수집하여 Streamlit 대시보드로 시각화
- **GitHub 레포**: https://github.com/Hwnagseunghwan/foodcarevblog-dashboard
- **로컬 경로**: `C:/foodcarevblog-dashboard/`
- **대시보드 실행**: `streamlit run dashboard.py` 또는 `대시보드실행.bat`

---

## 주요 파일

| 파일 | 역할 |
|------|------|
| `dashboard.py` | Streamlit 대시보드 메인 (탭 4개) |
| `naver_scraper.py` | 매일 23:00 KST 일별 조회수 자동 수집 |
| `collect_history.py` | 과거 3년치 일별/월별 데이터 일괄 수집 |
| `blog_visitors.json` | 일별 조회수 데이터 (최근 90일+) |
| `blog_visitors_monthly.json` | 월별 조회수 데이터 (2022-12~) |
| `naver_cookies.json` | 네이버 로그인 쿠키 (로컬용) |
| `.github/workflows/scraper.yml` | GitHub Actions 자동 수집 워크플로우 |

---

## 대시보드 탭 구성

### 탭1 - 📆 월별 추이 (6개월)
- 최근 6개월 조회수 카드 (전월 대비 증감률 포함)
- Altair 바 차트 (조회수 숫자 표시)
- 월별 원본 데이터 / CSV 다운로드

### 탭2 - 📅 주간 현황 (최근 90일)
- ISO 주차 기준 (엑셀 ISOWEEKNUM 동일, 월요일 시작)
- 최근 12주 조회수 카드 (전주 대비 증감률 포함)
- Altair 바 차트 (조회수 숫자 표시)
- 주간 데이터 테이블 / CSV 다운로드

### 탭3 - 📋 일간 현황 (최근 14일)
- 최근 14일 조회수 카드 (전일 대비 증감률 포함)
- 요일 표시: 토요일 🔵 파란색, 일요일/공휴일 🔴 빨간색
- Altair 바 차트 (요일별 색상 + 조회수 숫자 표시)
- 한국 공휴일 2025~2026 하드코딩 적용

### 탭4 - 💡 시사점
- **현재 진행 중인 월/주/일 제외, 완료된 기간만 분석**
- 순서: 종합 의견(날짜 포함) → 월별 동향 → 주간 동향 → 일간 동향
- 데이터 업데이트 시 자동 재계산

---

## 자동 수집 구조

### GitHub Actions (`scraper.yml`)
- **스케줄**: 매일 UTC 14:00 (KST 23:00)
- **인증**: `NAVER_COOKIES` Secret (로컬에서 추출한 쿠키 JSON)
- **수집 방식**: Playwright로 `blog.stat.naver.com/api/blog/daily/cv` API 호출
- **저장**: `blog_visitors.json` 커밋 & 푸시 (github-actions[bot])

### GitHub Secrets 등록 항목
- `NAVER_ID`, `NAVER_PW`, `BLOG_ID`, `NAVER_COOKIES`

---

## 환경 변수 (.env)
```
NAVER_ID=nature_food
NAVER_PW=Foodcare!@#
BLOG_ID=nature_food
```

---

## 수집 데이터 현황 (2026-03-16 기준)
- 일별: 91일치 (2025-12-16 ~ 2026-03-16)
- 월별: 38개월치 (2022-12 ~ 2026-02)
- 연도별: 2023년 / 2024년(300,134) / 2025년(203,961) / 2026년(38,175)

---

## 앞으로 추가 예정 작업

### Google Sheets 연동 대시보드
- Google Sheets에 쌓인 데이터를 `gspread`로 불러와 추가 탭 또는 별도 섹션 구성
- `gspread` + `google-auth` 패키지 사용
- Google Service Account 키를 GitHub Secret으로 등록 예정
- 연동할 시트 정보: (추후 사용자에게 확인 필요)

### 기타 개선 예정
- 공휴일 데이터를 `holidays` 패키지로 동적 처리 (현재 하드코딩)
- 스크래퍼 쿠키 만료 시 자동 갱신 방안

---

## 기술 스택
- Python 3.11
- Streamlit, Pandas, Altair
- Playwright (브라우저 자동화)
- GitHub Actions (CI/CD 스케줄러)
- gspread (Google Sheets 예정)
