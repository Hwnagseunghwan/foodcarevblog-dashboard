#!/usr/bin/env python3
"""
네이버 블로그 조회수 대시보드
실행: streamlit run dashboard.py
"""

import os
import json
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
from datetime import datetime, timedelta

DATA_FILE = "blog_visitors.json"
MONTHLY_FILE = "blog_visitors_monthly.json"

st.set_page_config(
    page_title="네이버 블로그 대시보드",
    page_icon="📊",
    layout="wide"
)

from dotenv import load_dotenv
load_dotenv()
BLOG_ID = os.environ.get("BLOG_ID", "nature_food")

# 자동 생성 사이드바 네비게이션 숨기고 커스텀 링크로 교체
st.markdown("""
<style>[data-testid="stSidebarNav"] { display: none; }</style>
""", unsafe_allow_html=True)
st.sidebar.markdown('<p style="font-size:28px; font-weight:900; font-family:\'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Malgun Gothic\', sans-serif; letter-spacing:-0.5px; margin:0;">Cle Dashboard</p>', unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.markdown('<p style="font-size:16px; color:#ccc; font-weight:700; font-family:\'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Malgun Gothic\', sans-serif; letter-spacing:0.5px; margin:0 0 12px 0;">— Cle Blog Dashboard</p>', unsafe_allow_html=True)
st.sidebar.page_link("dashboard.py", label="📊 Cle Blog Views")
st.sidebar.page_link("pages/vola_dashboard.py", label="🔗 Cle Blog Vola Tracker")
st.sidebar.page_link("pages/work_dashboard.py", label="📋 Cle Blog Work Tracker")
st.sidebar.divider()
st.sidebar.markdown('<p style="font-size:16px; color:#ccc; font-weight:700; font-family:\'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Malgun Gothic\', sans-serif; letter-spacing:0.5px; margin:0 0 12px 0;">— Cle Seeding Dashboard</p>', unsafe_allow_html=True)
st.sidebar.page_link("pages/seeding_dashboard.py", label="🌱 Seeding Work Dashboard")

st.markdown("<a id='cle-blog-dashboard'></a>", unsafe_allow_html=True)
st.title(f"📊 Cle 공식블로그 조회수 대시보드({BLOG_ID})")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


@st.cache_data(ttl=300)
def load_daily_data():
    if not Path(DATA_FILE).exists():
        return pd.DataFrame()
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(list(raw.items()), columns=["date", "views"])
    df["date"] = pd.to_datetime(df["date"])
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("date").reset_index(drop=True)
    return df


@st.cache_data(ttl=300)
def load_monthly_data():
    if not Path(MONTHLY_FILE).exists():
        return pd.DataFrame()
    with open(MONTHLY_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(list(raw.items()), columns=["month", "views"])
    df["month"] = pd.to_datetime(df["month"])
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("month").reset_index(drop=True)
    return df





tab2, tab1, tab3, tab4 = st.tabs(["📆 월별 추이 (6개월)", "📅 주간 현황 (최근 90일)", "📋 일간 현황 (최근 14일)", "💡 시사점"])

# ── 탭1: 주간 현황 ──────────────────────────────────────
with tab1:
    df = load_daily_data()

    if df.empty:
        st.warning("일별 데이터가 없습니다. naver_scraper.py를 먼저 실행해주세요.")
    else:
        # ISO 주차 컬럼 생성 (엑셀 ISOWEEKNUM 기준: 월요일 시작)
        iso = df["date"].dt.isocalendar()
        df["iso_year"] = iso["year"]
        df["iso_week"] = iso["week"]
        # 주 시작일(월요일) 계산
        df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="D")
        df["week_label"] = df["week_start"].dt.strftime("%Y-%m-%d") + \
                           " (W" + df["iso_week"].astype(str).str.zfill(2) + ")"

        # 주간 합산
        weekly = df.groupby(["week_start", "week_label"], sort=True)["views"].sum().reset_index()
        weekly.columns = ["week_start", "week_label", "views"]

        # 시작 주차 선택 반영 (선택 주차부터 12주)
        _week_labels = weekly["week_label"].tolist()
        _default_w = _week_labels[-12] if len(_week_labels) >= 12 else _week_labels[0]
        start_wl = st.session_state.get("weekly_start", _default_w)
        start_wi = weekly[weekly["week_label"] >= start_wl].index
        if len(start_wi) == 0:
            start_wi = weekly.index[-12:]
        recent_12w = weekly.loc[start_wi[:12]].reset_index(drop=True)
        # 증감률용 직전 1주 포함
        prev_wi = start_wi[0] - 1
        prev_week = weekly.loc[[prev_wi]] if prev_wi >= 0 else pd.DataFrame(columns=weekly.columns)
        recent_13w = pd.concat([prev_week, recent_12w]).reset_index(drop=True)

        st.subheader(f"주간 조회수 합계 ({start_wl.split(' ')[0]} ~)")
        cols = st.columns(len(recent_12w))
        for i, row in recent_12w.iterrows():
            prev_views = int(recent_13w.loc[i, "views"]) if len(recent_13w) > i else None
            curr_views = int(recent_13w.loc[i + 1, "views"]) if len(recent_13w) > i + 1 else int(row["views"])
            if prev_views and prev_views > 0:
                rate = (curr_views - prev_views) / prev_views * 100
                delta = f"{rate:+.1f}%"
            else:
                delta = None
            cols[i].metric(row["week_label"], f"{curr_views:,}", delta)

        st.divider()

        # 주간 조회수 추이 차트 (최근 12주, 숫자 표시)
        st.subheader(f"주간 조회수 추이 ({start_wl.split(' ')[0]} ~)")
        bar = alt.Chart(recent_12w).mark_bar().encode(
            x=alt.X("week_label:N", sort=None, title="주차", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("views:Q", title="조회수"),
            tooltip=["week_label", "views"]
        )
        text = alt.Chart(recent_12w).mark_text(dy=-8, fontSize=11).encode(
            x=alt.X("week_label:N", sort=None),
            y=alt.Y("views:Q"),
            text=alt.Text("views:Q", format=",")
        )
        st.altair_chart(bar + text, use_container_width=True)

        # 주간 데이터 테이블
        with st.expander("주간 데이터 보기"):
            table_w = weekly[["week_label", "views"]].copy()
            table_w.columns = ["주 시작일 (ISO주차)", "조회수"]
            table_w = table_w.sort_values("주 시작일 (ISO주차)", ascending=False).reset_index(drop=True)
            st.dataframe(table_w, use_container_width=True, height=300)

            csv = table_w.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv, file_name="blog_views_weekly.csv", mime="text/csv")

        st.divider()

        # ── 주간 현황 시작 주차 선택 (주간 데이터 보기 하단) ──────────────────────────────────────
        _week_options = weekly["week_label"].tolist()
        _default_week = _week_options[-12] if len(_week_options) >= 12 else _week_options[0]
        with st.form("weekly_selector"):
            col_w1, col_w2 = st.columns([2, 1])
            selected_week_start = col_w1.selectbox(
                "📅 주간 현황 시작 주차 선택",
                options=_week_options,
                index=_week_options.index(st.session_state.get("weekly_start", _default_week)),
                help="선택한 주차부터 이후 12주를 위 차트에 표시합니다."
            )
            col_w2.markdown("<br>", unsafe_allow_html=True)
            submitted_week = col_w2.form_submit_button("적용", use_container_width=True)
        if "weekly_start" not in st.session_state or submitted_week:
            st.session_state["weekly_start"] = selected_week_start
            if submitted_week:
                st.rerun()

# ── 탭3: 일간 현황 ──────────────────────────────────────

# 한국 공휴일 (2025~2026)
KR_HOLIDAYS = {
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30",
    "2025-03-01", "2025-05-05", "2025-05-06", "2025-06-06",
    "2025-08-15", "2025-10-03", "2025-10-05", "2025-10-06", "2025-10-07",
    "2025-10-09", "2025-12-25",
    "2026-01-01", "2026-02-17", "2026-02-18", "2026-02-19",
    "2026-03-01", "2026-05-05", "2026-05-24", "2026-06-06",
    "2026-08-15", "2026-09-24", "2026-09-25", "2026-09-26",
    "2026-10-03", "2026-10-09", "2026-12-25",
}
DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

def day_type(d):
    ds = d.strftime("%Y-%m-%d")
    if ds in KR_HOLIDAYS:
        return "holiday"
    if d.weekday() == 5:
        return "saturday"
    if d.weekday() == 6:
        return "sunday"
    return "weekday"

def date_label(d):
    dow = DAY_KO[d.weekday()]
    ds = d.strftime("%Y-%m-%d")
    if ds in KR_HOLIDAYS:
        return f"{d.strftime('%m/%d')}(공휴)"
    return f"{d.strftime('%m/%d')}({dow})"

with tab3:
    df3 = load_daily_data()

    if df3.empty:
        st.warning("일별 데이터가 없습니다. naver_scraper.py를 먼저 실행해주세요.")
    else:
        # 시작일 선택 반영 (선택일 포함 이후 14일)
        daily_start_str = st.session_state.get("daily_start", df3["date"].dt.strftime("%Y-%m-%d").iloc[-14])
        start_di = df3[df3["date"].dt.strftime("%Y-%m-%d") >= daily_start_str].index
        if len(start_di) == 0:
            start_di = df3.index[-14:]
        recent_14 = df3.loc[start_di[:14]].reset_index(drop=True)
        # 증감률용 직전 1일 포함
        prev_di = start_di[0] - 1
        prev_day = df3.loc[[prev_di]] if prev_di >= 0 else pd.DataFrame(columns=df3.columns)
        recent_15 = pd.concat([prev_day, recent_14]).reset_index(drop=True)

        recent_14["day_type"] = recent_14["date"].apply(day_type)
        recent_14["date_label"] = recent_14["date"].apply(date_label)

        # 일간 조회수 합계 + 증감률
        st.subheader(f"일간 조회수 ({daily_start_str} ~)")
        cols = st.columns(len(recent_14))
        for i, row in recent_14.iterrows():
            prev_views = int(recent_15.loc[i, "views"]) if len(recent_15) > i else None
            curr_views = int(recent_15.loc[i + 1, "views"]) if len(recent_15) > i + 1 else int(row["views"])
            if prev_views and prev_views > 0:
                rate = (curr_views - prev_views) / prev_views * 100
                delta = f"{rate:+.1f}%"
            else:
                delta = None
            dt = row["day_type"]
            prefix = "🔵 " if dt == "saturday" else "🔴 " if dt in ("sunday", "holiday") else ""
            cols[i].metric(f"{prefix}{row['date_label']}", f"{curr_views:,}", delta)

        st.divider()

        # 일간 조회수 추이 차트 (숫자 표시 + 요일 색상)
        st.subheader(f"일간 조회수 추이 ({daily_start_str} ~)")
        color_map = {"weekday": "#4C78A8", "saturday": "#1f77b4", "sunday": "#d62728", "holiday": "#d62728"}
        recent_14["bar_color"] = recent_14["day_type"].map(color_map)

        bar_d = alt.Chart(recent_14).mark_bar().encode(
            x=alt.X("date_label:N", sort=None, title="날짜", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("views:Q", title="조회수"),
            color=alt.Color("day_type:N", scale=alt.Scale(
                domain=["weekday", "saturday", "sunday", "holiday"],
                range=["#4C78A8", "#5B9BD5", "#d62728", "#d62728"]
            ), legend=alt.Legend(title="구분", labelExpr=(
                "datum.value === 'weekday' ? '평일' : datum.value === 'saturday' ? '토요일' : '일요일/공휴일'"
            ))),
            tooltip=["date_label", "views", "day_type"]
        )
        text_d = alt.Chart(recent_14).mark_text(dy=-8, fontSize=11).encode(
            x=alt.X("date_label:N", sort=None),
            y=alt.Y("views:Q"),
            text=alt.Text("views:Q", format=",")
        )
        st.altair_chart(bar_d + text_d, use_container_width=True)

        # 일별 원본 데이터 보기
        with st.expander("일별 원본 데이터 보기"):
            table_d = recent_14.copy()
            table_d["date"] = table_d["date"].dt.strftime("%Y-%m-%d")
            table_d = table_d[["date", "date_label", "views"]].copy()
            table_d.columns = ["날짜", "날짜(요일)", "조회수"]
            table_d = table_d.sort_values("날짜", ascending=False).reset_index(drop=True)
            st.dataframe(table_d, use_container_width=True, height=300)

            csv_d = table_d.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv_d, file_name="blog_views_daily.csv", mime="text/csv")

        st.divider()

        # ── 일간 현황 시작일 선택 (차트 하단) ──────────────────────────────────────
        _date_options = [d.strftime("%Y-%m-%d") for d in df3["date"].dt.date]
        _default_daily = _date_options[-14] if len(_date_options) >= 14 else _date_options[0]
        with st.form("daily_selector"):
            col_d1, col_d2 = st.columns([2, 1])
            selected_daily_start = col_d1.selectbox(
                "📋 일간 현황 시작일 선택",
                options=_date_options,
                index=_date_options.index(st.session_state.get("daily_start", _default_daily)),
                help="선택한 날부터 이후 14일을 위 차트에 표시합니다."
            )
            col_d2.markdown("<br>", unsafe_allow_html=True)
            submitted_daily = col_d2.form_submit_button("적용", use_container_width=True)
        if "daily_start" not in st.session_state or submitted_daily:
            st.session_state["daily_start"] = selected_daily_start
            if submitted_daily:
                st.rerun()

# ── 탭2: 월별 추이 ──────────────────────────────────────
with tab2:
    mdf = load_monthly_data()

    if mdf.empty:
        st.warning("월별 데이터가 없습니다. collect_history.py를 먼저 실행해주세요.")
    else:
        mdf["year"] = mdf["month"].dt.year
        mdf["year_month"] = mdf["month"].dt.strftime("%Y-%m")

        # 시작월 선택 반영 (선택월 포함 이후 6개월)
        start_ym = st.session_state.get("monthly_start", mdf["year_month"].iloc[-6])
        start_idx = mdf[mdf["year_month"] >= start_ym].index
        if len(start_idx) == 0:
            start_idx = mdf.index[-6:]
        recent_6m = mdf.loc[start_idx[:6]]

        # 증감률 계산용: 시작월 직전 1개월 포함
        prev_idx = start_idx[0] - 1
        prev_row = mdf.loc[[prev_idx]] if prev_idx >= 0 else pd.DataFrame()
        recent_7m = pd.concat([prev_row, recent_6m]).reset_index(drop=True)
        recent_6m = recent_6m.reset_index(drop=True)

        st.subheader(f"월별 조회수 합계 ({start_ym} ~)")
        cols = st.columns(len(recent_6m))
        for i, row in recent_6m.iterrows():
            prev_views = int(recent_7m.loc[i, "views"]) if len(recent_7m) > i else None
            curr_views = int(recent_7m.loc[i + 1, "views"]) if len(recent_7m) > i + 1 else int(row["views"])
            if prev_views and prev_views > 0:
                rate = (curr_views - prev_views) / prev_views * 100
                delta = f"{rate:+.1f}%"
            else:
                delta = None
            cols[i].metric(row["year_month"], f"{curr_views:,}", delta)

        st.divider()

        # 월별 바 차트 (선택 시작월부터 6개월, 숫자 표시)
        st.subheader(f"월별 조회수 추이 ({start_ym} ~)")
        bar_m = alt.Chart(recent_6m).mark_bar().encode(
            x=alt.X("year_month:N", sort=None, title="월", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("views:Q", title="조회수"),
            tooltip=["year_month", "views"]
        )
        text_m = alt.Chart(recent_6m).mark_text(dy=-8, fontSize=11).encode(
            x=alt.X("year_month:N", sort=None),
            y=alt.Y("views:Q"),
            text=alt.Text("views:Q", format=",")
        )
        st.altair_chart(bar_m + text_m, use_container_width=True)

        # 전체 데이터 다운로드
        with st.expander("월별 원본 데이터 보기"):
            all_monthly = mdf[["year_month", "views"]].copy()
            all_monthly.columns = ["연월", "조회수"]
            all_monthly = all_monthly.sort_values("연월", ascending=False).reset_index(drop=True)
            st.dataframe(all_monthly, use_container_width=True, height=300)

            csv_m = all_monthly.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("월별 CSV 다운로드", data=csv_m, file_name="blog_views_monthly.csv", mime="text/csv")

        st.divider()

        # ── 월별 추이 시작월 선택 (월별 원본 데이터 보기 하단) ──────────────────────────────────────
        month_options = sorted(mdf["year_month"].tolist())
        default_start = month_options[-6] if len(month_options) >= 6 else month_options[0]
        with st.form("month_selector"):
            col_m1, col_m2 = st.columns([2, 1])
            selected_start = col_m1.selectbox(
                "📆 월별 추이 시작월 선택",
                options=month_options,
                index=month_options.index(st.session_state.get("monthly_start", default_start)),
                help="선택한 달부터 이후 6개월을 위 차트에 표시합니다."
            )
            col_m2.markdown("<br>", unsafe_allow_html=True)
            submitted = col_m2.form_submit_button("적용", use_container_width=True)
        if "monthly_start" not in st.session_state or submitted:
            st.session_state["monthly_start"] = selected_start
            if submitted:
                st.rerun()

# ── 탭4: 시사점 ──────────────────────────────────────
with tab4:
    df4 = load_daily_data()
    mdf4 = load_monthly_data()

    if df4.empty or mdf4.empty:
        st.warning("데이터가 부족합니다.")
    else:
        # ── 데이터 준비 (현재 진행 중인 월/주/일 제외 → 완료된 기간만 분석) ──

        # 월별: 현재 월 제외 → 완료된 최근 월 기준
        mdf4["year_month"] = mdf4["month"].dt.strftime("%Y-%m")
        cur_month = datetime.now().strftime("%Y-%m")
        mdf4_done = mdf4[mdf4["year_month"] < cur_month].reset_index(drop=True)
        m_last = mdf4_done.iloc[-1]
        m_prev = mdf4_done.iloc[-2]
        m_rate = (m_last["views"] - m_prev["views"]) / m_prev["views"] * 100 if m_prev["views"] > 0 else 0
        m_trend = mdf4_done.tail(6)["views"].tolist()
        m_up_count = sum(1 for i in range(1, len(m_trend)) if m_trend[i] > m_trend[i-1])
        m_down_count = len(m_trend) - 1 - m_up_count

        # 주간: 현재 진행 중인 주 제외 → 완료된 최근 주 기준
        iso4 = df4["date"].dt.isocalendar()
        df4["iso_week"] = iso4["week"]
        df4["week_start"] = df4["date"] - pd.to_timedelta(df4["date"].dt.dayofweek, unit="D")
        df4["week_label"] = df4["week_start"].dt.strftime("%Y-%m-%d") + \
                            " (W" + df4["iso_week"].astype(str).str.zfill(2) + ")"
        weekly4 = df4.groupby(["week_start", "week_label"], sort=True)["views"].sum().reset_index()
        today_week_start = (datetime.now().date() - timedelta(days=datetime.now().weekday()))
        weekly4_done = weekly4[weekly4["week_start"].dt.date < today_week_start].reset_index(drop=True)
        w_last = weekly4_done.iloc[-1]
        w_prev = weekly4_done.iloc[-2]
        w_rate = (w_last["views"] - w_prev["views"]) / w_prev["views"] * 100 if w_prev["views"] > 0 else 0
        w12 = weekly4_done.tail(12)
        w_max = w12.loc[w12["views"].idxmax()]
        w_min = w12.loc[w12["views"].idxmin()]
        w_avg = w12["views"].mean()

        # 일간: 오늘 제외 → 완료된 최근 14일 기준 (스크래퍼가 전일 데이터 수집이므로 tail(14) 그대로 사용)
        today_str = datetime.now().strftime("%Y-%m-%d")
        df4_done = df4[df4["date"].dt.strftime("%Y-%m-%d") < today_str].reset_index(drop=True)
        d14 = df4_done.tail(14).reset_index(drop=True)
        d_last = d14.iloc[-1]
        d_prev = d14.iloc[-2]
        d_rate = (d_last["views"] - d_prev["views"]) / d_prev["views"] * 100 if d_prev["views"] > 0 else 0
        d7_avg = d14.tail(7)["views"].mean()
        d7_prev_avg = d14.head(7)["views"].mean()
        d7_rate = (d7_avg - d7_prev_avg) / d7_prev_avg * 100 if d7_prev_avg > 0 else 0
        d_max = d14.loc[d14["views"].idxmax()]
        d_min = d14.loc[d14["views"].idxmin()]

        # ── 리포트 출력 ──
        st.subheader(f"블로그 조회수 시사점 리포트")
        st.caption(f"기준일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')} | 현재 진행 중인 월/주/일 제외, 완료된 기간 기준 분석")

        st.divider()

        # 종합 의견
        analysis_date = datetime.now().strftime("%Y-%m-%d")
        st.markdown(f"#### 🔍 {analysis_date} 종합 의견")
        signals = []
        if m_rate > 5:
            signals.append("월별 조회수가 전월 대비 5% 이상 증가하며 성장세를 보이고 있습니다.")
        elif m_rate < -5:
            signals.append("월별 조회수가 전월 대비 5% 이상 감소하여 콘텐츠 전략 점검이 필요합니다.")
        else:
            signals.append("월별 조회수는 전월과 유사한 수준으로 안정적입니다.")

        if w_rate > 10:
            signals.append("주간 조회수가 전주 대비 10% 이상 급증하고 있어 특정 콘텐츠의 반응이 좋을 수 있습니다.")
        elif w_rate < -10:
            signals.append("주간 조회수가 전주 대비 10% 이상 감소하여 주의가 필요합니다.")
        else:
            signals.append("주간 조회수는 전주 대비 안정적인 수준을 유지하고 있습니다.")

        if d7_rate > 0:
            signals.append(f"최근 7일 평균이 직전 7일 대비 {abs(d7_rate):.1f}% 상승하며 단기 반등 신호가 나타나고 있습니다.")
        else:
            signals.append(f"최근 7일 평균이 직전 7일 대비 {abs(d7_rate):.1f}% 하락하고 있어 콘텐츠 업로드 주기 확인을 권장합니다.")

        for s in signals:
            st.markdown(f"- {s}")

        st.divider()

        # 월별 시사점
        st.markdown("#### 📆 월별 동향")
        m_arrow = "▲" if m_rate >= 0 else "▼"
        m_color = "🟢" if m_rate >= 0 else "🔴"
        st.markdown(f"""
- **최근 월 ({m_last['year_month']})** 조회수: **{int(m_last['views']):,}**회 {m_color} 전월 대비 **{m_arrow} {abs(m_rate):.1f}%**
- 최근 6개월 중 전월 대비 상승한 달: **{m_up_count}개월**, 하락한 달: **{m_down_count}개월**
- 6개월 평균 조회수: **{mdf4_done.tail(6)['views'].mean():,.0f}**회 / 월
- {"📈 최근 6개월 전반적으로 **상승 추세**입니다." if m_up_count > m_down_count else "📉 최근 6개월 전반적으로 **하락 추세**입니다." if m_down_count > m_up_count else "📊 최근 6개월 **보합세**를 유지하고 있습니다."}
        """)

        st.divider()

        # 주간 시사점
        st.markdown("#### 📅 주간 동향")
        w_arrow = "▲" if w_rate >= 0 else "▼"
        w_color = "🟢" if w_rate >= 0 else "🔴"
        st.markdown(f"""
- **최근 주 ({w_last['week_label']})** 조회수: **{int(w_last['views']):,}**회 {w_color} 전주 대비 **{w_arrow} {abs(w_rate):.1f}%**
- 최근 12주 평균 주간 조회수: **{w_avg:,.0f}**회
- 최근 12주 **최고** 주간 조회수: **{int(w_max['views']):,}**회 ({w_max['week_label']})
- 최근 12주 **최저** 주간 조회수: **{int(w_min['views']):,}**회 ({w_min['week_label']})
- {"📈 최근 주 조회수가 평균을 **상회**하고 있습니다." if w_last['views'] >= w_avg else "📉 최근 주 조회수가 평균을 **하회**하고 있습니다."}
        """)

        st.divider()

        # 일간 시사점
        st.markdown("#### 📋 일간 동향")
        d_arrow = "▲" if d_rate >= 0 else "▼"
        d_color = "🟢" if d_rate >= 0 else "🔴"
        d7_arrow = "▲" if d7_rate >= 0 else "▼"
        st.markdown(f"""
- **최근일 ({d_last['date'].strftime('%Y-%m-%d')})** 조회수: **{int(d_last['views']):,}**회 {d_color} 전일 대비 **{d_arrow} {abs(d_rate):.1f}%**
- 최근 7일 평균: **{d7_avg:,.0f}**회 / 직전 7일 평균: **{d7_prev_avg:,.0f}**회 → {d7_arrow} **{abs(d7_rate):.1f}%**
- 최근 14일 **최고**: **{int(d_max['views']):,}**회 ({d_max['date'].strftime('%Y-%m-%d')})
- 최근 14일 **최저**: **{int(d_min['views']):,}**회 ({d_min['date'].strftime('%Y-%m-%d')})
        """)

# ── 사이드바 ──────────────────────────────────────
st.sidebar.divider()
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()
