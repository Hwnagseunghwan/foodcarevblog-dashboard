#!/usr/bin/env python3
"""
네이버 블로그 조회수 대시보드
실행: streamlit run dashboard.py
"""

import os
import json
import pandas as pd
import streamlit as st
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
BLOG_ID = os.environ.get("BLOG_ID", "zen896")
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


tab1, tab2 = st.tabs(["📅 일별 현황 (최근 90일)", "📆 월별 추이 (3년)"])

# ── 탭1: 일별 현황 ──────────────────────────────────────
with tab1:
    df = load_daily_data()

    if df.empty:
        st.warning("일별 데이터가 없습니다. naver_scraper.py를 먼저 실행해주세요.")
    else:
        # 기간 필터
        col_f1, col_f2 = st.columns(2)
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        start = col_f1.date_input("시작일", value=min_date, min_value=min_date, max_value=max_date, key="daily_start")
        end = col_f2.date_input("종료일", value=max_date, min_value=min_date, max_value=max_date, key="daily_end")

        filtered = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

        # 요약 지표
        total = int(filtered["views"].sum())
        avg = filtered["views"].mean()
        max_val = int(filtered["views"].max()) if not filtered.empty else 0
        max_date_val = filtered.loc[filtered["views"].idxmax(), "date"].strftime("%Y-%m-%d") if not filtered.empty else "-"
        recent_7 = int(filtered.tail(7)["views"].sum())

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 조회수", f"{total:,}")
        col2.metric("일평균 조회수", f"{avg:.1f}")
        col3.metric("최고 조회수", f"{max_val:,}", max_date_val)
        col4.metric("최근 7일 조회수", f"{recent_7:,}")

        st.divider()

        # 시계열 차트
        st.subheader("일별 조회수 추이")
        chart_df = filtered.set_index("date")[["views"]]
        st.line_chart(chart_df, use_container_width=True, height=350)

        # 주간 합계
        st.subheader("주간 조회수 합계")
        weekly = filtered.copy()
        weekly["week"] = weekly["date"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%Y-%m-%d"))
        weekly_sum = weekly.groupby("week")["views"].sum().reset_index()
        weekly_sum.columns = ["주 시작일", "조회수"]
        st.bar_chart(weekly_sum.set_index("주 시작일"), use_container_width=True, height=250)

        # 데이터 테이블
        with st.expander("원본 데이터 보기"):
            table = filtered.copy()
            table["date"] = table["date"].dt.strftime("%Y-%m-%d")
            table.columns = ["날짜", "조회수"]
            table = table.sort_values("날짜", ascending=False).reset_index(drop=True)
            st.dataframe(table, use_container_width=True, height=300)

            csv = table.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv, file_name="blog_views_daily.csv", mime="text/csv")

# ── 탭2: 월별 추이 ──────────────────────────────────────
with tab2:
    mdf = load_monthly_data()

    if mdf.empty:
        st.warning("월별 데이터가 없습니다. collect_history.py를 먼저 실행해주세요.")
    else:
        # 연도별 요약
        mdf["year"] = mdf["month"].dt.year
        mdf["year_month"] = mdf["month"].dt.strftime("%Y-%m")

        yearly = mdf.groupby("year")["views"].sum().reset_index()
        yearly.columns = ["연도", "총 조회수"]

        st.subheader("연도별 조회수 합계")
        cols = st.columns(len(yearly))
        for i, row in yearly.iterrows():
            cols[i].metric(f"{int(row['연도'])}년", f"{int(row['총 조회수']):,}")

        st.divider()

        # 월별 바 차트
        st.subheader("월별 조회수 추이 (전체)")
        monthly_chart = mdf.set_index("year_month")[["views"]]
        monthly_chart.index.name = "월"
        monthly_chart.columns = ["조회수"]
        st.bar_chart(monthly_chart, use_container_width=True, height=350)

        # 연도 선택 필터
        st.subheader("연도별 상세 조회")
        years = sorted(mdf["year"].unique(), reverse=True)
        selected_year = st.selectbox("연도 선택", years)

        year_data = mdf[mdf["year"] == selected_year].copy()
        year_data["월"] = year_data["month"].dt.strftime("%m월")

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.bar_chart(year_data.set_index("월")[["views"]].rename(columns={"views": "조회수"}),
                         use_container_width=True, height=280)
        with col_b:
            table_y = year_data[["월", "views"]].copy()
            table_y.columns = ["월", "조회수"]
            table_y = table_y.sort_values("월", ascending=False).reset_index(drop=True)
            st.dataframe(table_y, use_container_width=True, height=280)

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
