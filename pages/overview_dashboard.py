#!/usr/bin/env python3
"""
Cle 마케팅 통합 성과 대시보드
"""
import sys
import json
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import require_login, show_user_sidebar

ROOT = Path(__file__).parent.parent

st.set_page_config(
    page_title="Cle 통합 성과 대시보드",
    page_icon="📈",
    layout="wide"
)

require_login()

# ── 사이드바 ──────────────────────────────────────────────────────
st.markdown("""
<style>[data-testid="stSidebarNav"] { display: none; }</style>
""", unsafe_allow_html=True)
st.sidebar.markdown('<p style="font-size:28px; font-weight:900; font-family:\'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Malgun Gothic\', sans-serif; letter-spacing:-0.5px; margin:0;">Cle Dashboard</p>', unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.page_link("pages/overview_dashboard.py", label="📈 바이럴 성과 대시보드")
st.sidebar.divider()
st.sidebar.markdown('<p style="font-size:16px; color:#ccc; font-weight:700; font-family:\'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Malgun Gothic\', sans-serif; letter-spacing:0.5px; margin:0 0 12px 0;">— Cle Blog Dashboard</p>', unsafe_allow_html=True)
st.sidebar.page_link("dashboard.py", label="📊 Cle Blog Views")
st.sidebar.page_link("pages/vola_dashboard.py", label="🔗 Cle Blog Vola Tracker")
st.sidebar.page_link("pages/work_dashboard.py", label="📋 Cle Blog Work Tracker")
st.sidebar.divider()
st.sidebar.markdown('<p style="font-size:16px; color:#ccc; font-weight:700; font-family:\'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Malgun Gothic\', sans-serif; letter-spacing:0.5px; margin:0 0 12px 0;">— Cle Seeding Dashboard</p>', unsafe_allow_html=True)
st.sidebar.page_link("pages/seeding_dashboard.py", label="🌱 Cle Seeding Work Tracker")
st.sidebar.page_link("pages/seeding_vola_dashboard.py", label="🔗 Cle Seeding Vola Tracker")
st.sidebar.divider()
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

show_user_sidebar()

st.sidebar.divider()
if "collect_msg" in st.session_state:
    msg = st.session_state.pop("collect_msg")
    ok = st.session_state.pop("collect_ok", True)
    st.sidebar.success(msg) if ok else st.sidebar.error(msg)
if st.sidebar.button("🔄 전체 데이터 재수집", use_container_width=True):
    import importlib.util, os
    _root = Path(__file__).parent.parent
    import json as _json
    for _k in ["GOOGLE_CREDENTIALS", "VOLA_API_KEY", "NAVER_COOKIES", "NAVER_ID", "NAVER_PW", "BLOG_ID"]:
        try:
            if _k not in os.environ:
                _v = st.secrets[_k]
                os.environ[_k] = _json.dumps(dict(_v)) if hasattr(_v, "items") else str(_v)
        except Exception:
            pass
    scrapers = [
        ("📊 Blog 조회수",      "naver_scraper.py"),
        ("🔗 Vola 클릭수",      "vola_scraper.py"),
        ("📋 Blog 업무시트",    "sheets_scraper.py"),
        ("🌱 Seeding 업무시트", "seeding_scraper.py"),
        ("🔗 Seeding Vola",     "seeding_vola_scraper.py"),
    ]
    status_box = st.sidebar.empty()
    errors = []
    prev_dir = os.getcwd()
    try:
        os.chdir(str(_root))
        for label, script in scrapers:
            status_box.info(f"⏳ {label} 수집 중...")
            try:
                spec = importlib.util.spec_from_file_location("_scraper_mod", _root / script)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.main()
            except Exception as e:
                errors.append(f"{label}: {str(e)[:120]}")
    finally:
        os.chdir(prev_dir)
    status_box.empty()
    st.session_state["collect_msg"] = ("오류: " + ", ".join(errors)) if errors else "전체 수집 완료!"
    st.session_state["collect_ok"] = not bool(errors)
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption("⚠️ 관리자외 전체 데이터재수집 버튼을 누르지 마세요.")


# ── 데이터 로드 ──────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all():
    # 1. 블로그 일별 조회수
    blog_daily = {}
    p = ROOT / "blog_visitors.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            blog_daily = json.load(f)

    # 2. 블로그 월별 조회수
    blog_monthly = {}
    p = ROOT / "blog_visitors_monthly.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            blog_monthly = json.load(f)

    # 3. Blog Vola 일별 클릭수
    blog_vola_daily = {}
    p = ROOT / "vola_clicks.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            vola_raw = json.load(f)
        for date_str, links in vola_raw.get("daily", {}).items():
            blog_vola_daily[date_str] = sum(v.get("daily_clicks", 0) for v in links.values())

    # 4. Blog 업무 데이터
    work_rows = []
    p = ROOT / "work_data.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            work_rows = json.load(f).get("rows", [])

    # 5. Seeding 업무 데이터
    seeding_rows = []
    p = ROOT / "seeding_data.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            seeding_rows = json.load(f).get("rows", [])

    # 6. Seeding Vola 일별 클릭수
    seeding_vola_rows = []
    p = ROOT / "seeding_vola_data.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            seeding_vola_rows = json.load(f).get("rows", [])

    return blog_daily, blog_monthly, blog_vola_daily, work_rows, seeding_rows, seeding_vola_rows


blog_daily, blog_monthly, blog_vola_daily, work_rows, seeding_rows, seeding_vola_rows = load_all()


# ── 전처리 ──────────────────────────────────────────────────────
def parse_date(s):
    s = str(s).strip()
    for fmt in ("%Y. %m. %d", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass
    return pd.NaT


def to_numeric_safe(v):
    try:
        return float(str(v).replace(",", "").replace("-", "0") or 0)
    except Exception:
        return 0.0


# 블로그 조회수 DataFrame
df_blog = pd.DataFrame(list(blog_daily.items()), columns=["date", "blog_views"])
df_blog["date"] = pd.to_datetime(df_blog["date"], errors="coerce")
df_blog["blog_views"] = pd.to_numeric(df_blog["blog_views"], errors="coerce").fillna(0).astype(int)
df_blog = df_blog.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

# Blog Vola 클릭 DataFrame
df_bvola = pd.DataFrame(list(blog_vola_daily.items()), columns=["date", "blog_vola_clicks"])
df_bvola["date"] = pd.to_datetime(df_bvola["date"], errors="coerce")
df_bvola["blog_vola_clicks"] = pd.to_numeric(df_bvola["blog_vola_clicks"], errors="coerce").fillna(0).astype(int)
df_bvola = df_bvola.dropna(subset=["date"])

# 업무 데이터 (블로그 + 시딩 통합)
def build_work_df(rows, source):
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # date 컬럼이 "12. 18" 형식이면 year 컬럼과 조합
    def parse_work_date(row):
        date_str = str(row.get("date", "")).strip()
        year_val = row.get("year", "")
        # 연도가 없는 경우 year 컬럼 붙여서 파싱
        if year_val and len(date_str) <= 7:
            full = f"{year_val}. {date_str}"
        else:
            full = date_str
        return parse_date(full)
    df["parsed_date"] = df.apply(parse_work_date, axis=1)
    df["source"] = source
    for col in ["원고비용", "작업비용", "송출비용"]:
        if col in df.columns:
            df[col] = df[col].apply(to_numeric_safe)
        else:
            df[col] = 0.0
    df["총비용"] = df["원고비용"] + df["작업비용"] + df["송출비용"]
    if "검색량(M)" in df.columns:
        df["검색량(M)"] = df["검색량(M)"].apply(to_numeric_safe)
    else:
        df["검색량(M)"] = 0.0
    df["노출"] = df.get("노출여부", pd.Series([""] * len(df))).apply(
        lambda x: 1 if str(x).strip() in ("노출", "Y", "y", "O", "o", "1") else 0
    )
    df["노출_검색량"] = df["검색량(M)"] * df["노출"]
    return df.dropna(subset=["parsed_date"])


df_work = build_work_df(work_rows, "블로그")
df_seed = build_work_df(seeding_rows, "시딩")
df_all_work = pd.concat([df_work, df_seed], ignore_index=True) if not (df_work.empty and df_seed.empty) else pd.DataFrame()

# Seeding Vola DataFrame
skip_cols = {"year", "month", "week", "date", "비고", "비고 "}
sv_vola_cols = []
df_sv = pd.DataFrame()
if seeding_vola_rows:
    df_sv = pd.DataFrame(seeding_vola_rows)
    df_sv["parsed_date"] = df_sv["date"].apply(parse_date)
    sv_vola_cols = [c for c in df_sv.columns if c not in skip_cols and c not in {"parsed_date"}
                    and ("http" in str(c).lower() or "vo.la" in str(c).lower())]
    for c in sv_vola_cols:
        df_sv[c] = df_sv[c].apply(to_numeric_safe)
    if sv_vola_cols:
        df_sv["seeding_vola_clicks"] = df_sv[sv_vola_cols].sum(axis=1)
    else:
        df_sv["seeding_vola_clicks"] = 0
    df_sv = df_sv.dropna(subset=["parsed_date"])


# ── 통합 일별 DataFrame ─────────────────────────────────────────
def make_daily_df():
    base = df_blog[["date", "blog_views"]].copy()

    if not df_bvola.empty:
        base = base.merge(df_bvola[["date", "blog_vola_clicks"]], on="date", how="left")
    else:
        base["blog_vola_clicks"] = 0

    if not df_sv.empty:
        sv_agg = df_sv.groupby("parsed_date")["seeding_vola_clicks"].sum().reset_index()
        sv_agg.columns = ["date", "seeding_vola_clicks"]
        base = base.merge(sv_agg, on="date", how="left")
    else:
        base["seeding_vola_clicks"] = 0

    if not df_all_work.empty:
        work_agg = df_all_work.groupby("parsed_date").agg(
            원고수=("NO", "count"),
            총비용=("총비용", "sum"),
            검색량=("검색량(M)", "sum"),
            노출수=("노출", "sum"),
            노출_검색량=("노출_검색량", "sum"),
        ).reset_index()
        work_agg.columns = ["date", "원고수", "총비용", "검색량", "노출수", "노출_검색량"]
        base = base.merge(work_agg, on="date", how="left")
    else:
        for col in ["원고수", "총비용", "검색량", "노출수", "노출_검색량"]:
            base[col] = 0

    base = base.fillna(0)
    base["총_vola_클릭"] = base["blog_vola_clicks"] + base["seeding_vola_clicks"]
    base["year_month"] = base["date"].dt.strftime("%Y-%m")
    base["week_label"] = (
        base["date"].dt.strftime("%Y-W")
        + base["date"].dt.isocalendar().week.astype(str).str.zfill(2)
    )
    return base


df_daily = make_daily_df()

if df_daily.empty:
    st.warning("데이터가 없습니다. 먼저 데이터를 수집해주세요.")
    st.stop()

# ── 페이지 헤더 ─────────────────────────────────────────────────
st.title("📈 Cle 마케팅 통합 성과 대시보드")
st.caption("블로그 · 시딩 · Vola 클릭 데이터를 종합한 마케팅 전체 성과 요약")
st.divider()

# ── 기간 선택기 ─────────────────────────────────────────────────
min_date = df_daily["date"].min().date()
max_date_val = df_daily["date"].max().date()

period_options = ["전체", "최근 30일", "최근 90일", "최근 6개월", "직접 선택"]
col_sel, col_range = st.columns([2, 3])
with col_sel:
    selected_period = st.selectbox("📅 조회 기간", period_options, index=0, key="kpi_period")

if selected_period == "최근 30일":
    date_from = max_date_val - timedelta(days=29)
    date_to = max_date_val
elif selected_period == "최근 90일":
    date_from = max_date_val - timedelta(days=89)
    date_to = max_date_val
elif selected_period == "최근 6개월":
    date_from = (pd.Timestamp(max_date_val) - pd.DateOffset(months=6)).date()
    date_to = max_date_val
elif selected_period == "직접 선택":
    with col_range:
        date_from, date_to = st.date_input(
            "날짜 범위",
            value=(max_date_val - timedelta(days=29), max_date_val),
            min_value=min_date,
            max_value=max_date_val,
            key="kpi_date_range"
        ) if True else (min_date, max_date_val)
    if not isinstance(date_from, type(date_to)):
        date_from, date_to = min_date, max_date_val
else:  # 전체
    date_from = min_date
    date_to = max_date_val

period_label = f"{date_from.strftime('%Y.%m.%d')} ~ {date_to.strftime('%Y.%m.%d')}"
df_filtered = df_daily[
    (df_daily["date"].dt.date >= date_from) &
    (df_daily["date"].dt.date <= date_to)
]

st.divider()

# ── 누적 KPI ────────────────────────────────────────────────────
total_views = int(df_filtered["blog_views"].sum())
total_vola = int(df_filtered["총_vola_클릭"].sum())
total_articles = int(df_filtered["원고수"].sum())
total_exposure = int(df_filtered["노출수"].sum())
total_search_vol = int(df_filtered["노출_검색량"].sum())

st.subheader(f"누적 성과  `{period_label}`")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📖 블로그 총 조회수", f"{total_views:,}")
c2.metric("🔗 총 Vola 클릭수", f"{total_vola:,}")
c3.metric("📝 총 원고 발행수", f"{total_articles:,}건")
c4.metric("🔍 노출 키워드 수", f"{total_exposure:,}건")
c5.metric("🔎 노출 키워드 검색량", f"{total_search_vol:,}")

# ── 블로그 vs 시딩 원고 발행 비중 ────────────────────────────────
st.divider()
df_work_f = df_work[
    (df_work["parsed_date"].dt.date >= date_from) &
    (df_work["parsed_date"].dt.date <= date_to)
] if not df_work.empty else df_work
df_seed_f = df_seed[
    (df_seed["parsed_date"].dt.date >= date_from) &
    (df_seed["parsed_date"].dt.date <= date_to)
] if not df_seed.empty else df_seed

if not df_work_f.empty and not df_seed_f.empty:
    st.subheader(f"📊 블로그 vs 시딩 원고 발행 비중  `{period_label}`")
    pie_data = pd.DataFrame({
        "채널": ["블로그", "시딩"],
        "원고수": [len(df_work_f), len(df_seed_f)]
    })
    col_p, _ = st.columns([1, 1])
    with col_p:
        pie = alt.Chart(pie_data).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("원고수:Q"),
            color=alt.Color("채널:N", scale=alt.Scale(
                domain=["블로그", "시딩"], range=["#4C78A8", "#54A24B"]
            )),
            tooltip=["채널", "원고수"]
        ).properties(height=240)
        st.altair_chart(pie, use_container_width=True)

# ── 종합 시사점 ──────────────────────────────────────────────────
st.divider()
st.subheader("🔍 종합 시사점")
st.caption(f"기준: {period_label}")

if len(df_filtered) > 0:
    insights = []

    if total_views > 0 and total_vola > 0:
        ctr_val = total_vola / total_views * 100
        if ctr_val >= 5:
            insights.append(("🔗 Vola 전환율", f"{ctr_val:.1f}% — 콘텐츠를 통한 사이트 유입이 활발하게 이루어지고 있습니다."))
        elif ctr_val >= 2:
            insights.append(("🔗 Vola 전환율", f"{ctr_val:.1f}% — CTA 문구나 링크 위치를 개선하면 유입을 더 높일 수 있습니다."))
        else:
            insights.append(("🔗 Vola 전환율", f"{ctr_val:.1f}% — 링크 노출 빈도와 위치 개선을 권장합니다."))

    if not df_work_f.empty and not df_seed_f.empty:
        blog_cnt = len(df_work_f)
        seed_cnt = len(df_seed_f)
        total_cnt = blog_cnt + seed_cnt
        insights.append(("📝 원고 발행", f"총 {total_cnt:,}건 · 블로그 {blog_cnt}건({blog_cnt/total_cnt*100:.0f}%) / 시딩 {seed_cnt}건({seed_cnt/total_cnt*100:.0f}%)"))

    if total_exposure > 0:
        insights.append(("🔍 키워드 노출", f"{total_exposure:,}건 — 브랜드 검색 접점이 지속 확대되고 있습니다."))

    insights.append(("🛒 전환 가능성", "Vola 클릭의 주요 목적지(이벤트·상품 페이지) 유입은 회원가입 및 구매 전환으로 이어질 가능성이 높습니다. 향후 전환 데이터(가입수·주문수) 연동 시 실제 ROI 측정이 가능합니다."))

    for title, body in insights:
        st.markdown(f"**{title}**")
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{body}")
        st.write("")
