#!/usr/bin/env python3
"""
Cle Seeding Vola Tracker 대시보드
"""

import sys
import json
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import require_login, show_user_sidebar

DATA_FILE = "seeding_vola_data.json"

st.set_page_config(
    page_title="Cle Seeding Vola Tracker",
    page_icon="🔗",
    layout="wide"
)

require_login()

# 사이드바 커스텀 네비게이션
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
    try:
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
    except Exception:
        pass
    scrapers = [
        ("🔗 Vola 클릭수",      "vola_scraper.py"),
        ("📋 Blog 업무시트",    "sheets_scraper.py"),
        ("🌱 Seeding 업무시트", "seeding_scraper.py"),
        ("🔗 Seeding Vola",     "seeding_vola_scraper.py"),
    ]
    status_box = st.sidebar.empty()
    errors = []
    prev_dir = os.getcwd()
    try:
        os.chdir(str(root))
        for label, script in scrapers:
            status_box.info(f"⏳ {label} 수집 중...")
            try:
                spec = importlib.util.spec_from_file_location("_scraper_mod", root / script)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.main()
            except Exception as e:
                errors.append(f"{label}: {str(e)[:120]}")
    finally:
        os.chdir(prev_dir)
    status_box.empty()
    st.session_state["collect_msg"] = ("오류:
" + "
".join(errors)) if errors else "전체 수집 완료!"
    st.session_state["collect_ok"] = not bool(errors)
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption("⚠️ 관리자외 전체 데이터재수집 버튼을 누르지 마세요.")

st.title("🔗 Cle Seeding Vola Tracker")


@st.cache_data(ttl=300)
def load_data(data_file):
    path = Path(__file__).parent.parent / data_file
    if not path.exists():
        return pd.DataFrame(), ""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw.get("rows", []))
    updated_at = raw.get("updated_at", "")
    return df, updated_at


df, updated_at = load_data(DATA_FILE)

if df.empty:
    st.warning("데이터가 없습니다. seeding_vola_scraper.py를 먼저 실행해주세요.")
    st.stop()

st.caption(f"마지막 업데이트: {updated_at}  |  전체 {len(df)}일")

# ── 전처리 ──────────────────────────────────────────────────────
# 날짜 파싱: "2026. 2. 1 " → Timestamp
df["parsed_date"] = pd.to_datetime(df["date"].astype(str).str.strip(), format="%Y. %m. %d", errors="coerce")
df["year_month"] = df["parsed_date"].dt.strftime("%Y-%m")
df["week_label"] = df["parsed_date"].dt.strftime("%Y-W") + df["parsed_date"].dt.isocalendar().week.astype(str).str.zfill(2)

# vola 컬럼 식별 (http 포함 또는 vo.la 포함 컬럼)
skip_cols = {"year", "month", "week", "date", "parsed_date", "year_month", "week_label"}
vola_cols = [
    c for c in df.columns
    if c not in skip_cols and ("http" in str(c).lower() or "vo.la" in str(c).lower())
]
# fallback: 날짜/메타 컬럼 제외한 나머지 숫자형 컬럼
if not vola_cols:
    meta_cols = {"year", "month", "week", "date", "비고", "비고 "}
    vola_cols = [c for c in df.columns if c not in meta_cols and c not in skip_cols]

# 컬럼명 → 라벨 매핑 (URL\n설명 → 설명만)
col_to_label = {}
for c in vola_cols:
    parts = str(c).split("\n")
    col_to_label[c] = parts[-1].strip() if len(parts) >= 2 else str(c).strip()

# "-" → 0, 숫자 변환
for c in vola_cols:
    df[c] = df[c].replace("-", 0)
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

# 라벨 컬럼명으로 rename한 복사본
label_cols = list(col_to_label.values())

if not label_cols:
    st.error("클릭수 데이터 컬럼을 찾을 수 없습니다. 데이터를 확인해주세요.")
    st.dataframe(df, use_container_width=True)
    st.stop()

df_labeled = df[["parsed_date", "year_month", "week_label"] + vola_cols].copy()
df_labeled = df_labeled.rename(columns=col_to_label)
df_labeled = df_labeled.dropna(subset=["parsed_date"])

tab1, tab2, tab3 = st.tabs(["📆 월별 추이", "📅 주간 현황", "📋 일간 현황"])


# ── 공통 차트 함수 ──────────────────────────────────────────────
def make_stacked_bar(data, x_col, x_title):
    melted = data.melt(id_vars=[x_col], value_vars=label_cols, var_name="링크", value_name="클릭수")
    total = melted.groupby(x_col)["클릭수"].sum().reset_index(name="합계")

    bar = alt.Chart(melted).mark_bar().encode(
        x=alt.X(f"{x_col}:N", sort=None, title=x_title, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("클릭수:Q", title="클릭수"),
        color=alt.Color("링크:N", title="링크"),
        tooltip=[x_col, "링크", "클릭수"]
    )
    text = alt.Chart(total).mark_text(dy=-8, fontSize=11).encode(
        x=alt.X(f"{x_col}:N", sort=None),
        y=alt.Y("합계:Q"),
        text=alt.Text("합계:Q")
    )
    return bar + text


# ── 탭1: 월별 추이 ──────────────────────────────────────────────
with tab1:
    max_date = df_labeled["parsed_date"].max()
    cutoff = (max_date - pd.DateOffset(months=5)).replace(day=1)
    df_m = df_labeled[df_labeled["parsed_date"] >= cutoff].copy()

    grp = df_m.groupby("year_month")[label_cols].sum().reset_index()

    # 상단 지표
    total_by_link = df_m[label_cols].sum()
    cols_m = st.columns(len(label_cols))
    for i, lbl in enumerate(label_cols):
        cols_m[i].metric(lbl, f"{int(total_by_link[lbl]):,}")

    st.divider()

    st.subheader("월별 링크별 클릭수 (최근 6개월)")
    st.altair_chart(make_stacked_bar(grp, "year_month", "월"), use_container_width=True)

    st.divider()

    # 링크별 월별 상세 테이블
    with st.expander("월별 상세 데이터 보기"):
        st.dataframe(grp.sort_values("year_month", ascending=False).reset_index(drop=True),
                     use_container_width=True)
        csv = grp.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("CSV 다운로드", data=csv, file_name="seeding_vola_monthly.csv", mime="text/csv")


# ── 탭2: 주간 현황 ──────────────────────────────────────────────
with tab2:
    max_date = df_labeled["parsed_date"].max()
    cutoff = max_date - pd.Timedelta(days=89)
    df_w = df_labeled[df_labeled["parsed_date"] >= cutoff].copy()

    grp_w = df_w.groupby("week_label")[label_cols].sum().reset_index()

    # 상단 지표
    total_by_link_w = df_w[label_cols].sum()
    cols_w = st.columns(len(label_cols))
    for i, lbl in enumerate(label_cols):
        cols_w[i].metric(lbl, f"{int(total_by_link_w[lbl]):,}")

    st.divider()

    st.subheader("주간별 링크별 클릭수 (최근 90일)")
    st.altair_chart(make_stacked_bar(grp_w, "week_label", "주차"), use_container_width=True)

    st.divider()

    with st.expander("주간별 상세 데이터 보기"):
        st.dataframe(grp_w.sort_values("week_label", ascending=False).reset_index(drop=True),
                     use_container_width=True)
        csv_w = grp_w.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("CSV 다운로드", data=csv_w, file_name="seeding_vola_weekly.csv", mime="text/csv")


# ── 탭3: 일간 현황 ──────────────────────────────────────────────
with tab3:
    max_date = df_labeled["parsed_date"].max()
    cutoff = max_date - pd.Timedelta(days=13)
    df_d = df_labeled[df_labeled["parsed_date"] >= cutoff].copy()
    df_d["date_str"] = df_d["parsed_date"].dt.strftime("%Y-%m-%d")

    grp_d = df_d.groupby("date_str")[label_cols].sum().reset_index()

    # 상단 지표
    total_by_link_d = df_d[label_cols].sum()
    cols_d = st.columns(len(label_cols))
    for i, lbl in enumerate(label_cols):
        cols_d[i].metric(lbl, f"{int(total_by_link_d[lbl]):,}")

    st.divider()

    st.subheader("일별 링크별 클릭수 (최근 14일)")
    st.altair_chart(make_stacked_bar(grp_d, "date_str", "날짜"), use_container_width=True)

    st.divider()

    with st.expander("일별 상세 데이터 보기"):
        st.dataframe(grp_d.sort_values("date_str", ascending=False).reset_index(drop=True),
                     use_container_width=True)
        csv_d = grp_d.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("CSV 다운로드", data=csv_d, file_name="seeding_vola_daily.csv", mime="text/csv")
