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
st.title(f"📊 네이버 블로그 {BLOG_ID} 조회수 대시보드")
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


tab2, tab1 = st.tabs(["📆 월별 추이 (6개월)", "📅 주간 현황 (최근 90일)"])

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

        # 주간 조회수 합계 + 증감률 (최근 12주)
        recent_13w = weekly.tail(13).reset_index(drop=True)  # 증감률 계산용 이전 주 포함
        recent_12w = weekly.tail(12).reset_index(drop=True)

        st.subheader("주간 조회수 합계")
        cols = st.columns(len(recent_12w))
        for i, row in recent_12w.iterrows():
            idx = len(recent_13w) - 12 + i
            prev_views = int(recent_13w.loc[idx - 1, "views"]) if idx > 0 else None
            curr_views = int(row["views"])
            if prev_views and prev_views > 0:
                rate = (curr_views - prev_views) / prev_views * 100
                delta = f"{rate:+.1f}%"
            else:
                delta = None
            cols[i].metric(row["week_label"], f"{curr_views:,}", delta)

        st.divider()

        # 주간 조회수 추이 차트 (최근 12주, 숫자 표시)
        st.subheader("주간 조회수 추이 (ISOWEEKNUM 기준)")
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

# ── 탭2: 월별 추이 ──────────────────────────────────────
with tab2:
    mdf = load_monthly_data()

    if mdf.empty:
        st.warning("월별 데이터가 없습니다. collect_history.py를 먼저 실행해주세요.")
    else:
        mdf["year"] = mdf["month"].dt.year
        mdf["year_month"] = mdf["month"].dt.strftime("%Y-%m")

        recent_6m = mdf.tail(6)

        # 월별 조회수 지표 (최근 6개월 + 전월 대비 증가율)
        recent_7m = mdf.tail(7).reset_index(drop=True)  # 증가율 계산용 이전달 포함
        st.subheader("월별 조회수 합계")
        cols = st.columns(len(recent_6m))
        for i, (_, row) in enumerate(recent_6m.iterrows()):
            idx = len(recent_7m) - 6 + i
            prev_views = int(recent_7m.loc[idx - 1, "views"]) if idx > 0 else None
            curr_views = int(row["views"])
            if prev_views and prev_views > 0:
                rate = (curr_views - prev_views) / prev_views * 100
                delta = f"{rate:+.1f}%"
            else:
                delta = None
            cols[i].metric(row["year_month"], f"{curr_views:,}", delta)

        st.divider()

        # 월별 바 차트 (최근 6개월, 숫자 표시)
        st.subheader("월별 조회수 추이 (최근 6개월)")
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

# ── 사이드바 ──────────────────────────────────────
st.sidebar.divider()
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()
