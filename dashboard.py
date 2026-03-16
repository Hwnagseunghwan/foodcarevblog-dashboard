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
def load_data():
    if not Path(DATA_FILE).exists():
        return pd.DataFrame()
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(list(raw.items()), columns=["date", "views"])
    df["date"] = pd.to_datetime(df["date"])
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("date").reset_index(drop=True)
    return df


df = load_data()

if df.empty:
    st.warning("데이터가 없습니다. naver_scraper.py를 먼저 실행해주세요.")
    st.stop()

# ── 기간 필터 ──────────────────────────────────────
st.sidebar.header("기간 설정")
min_date = df["date"].min().date()
max_date = df["date"].max().date()

start = st.sidebar.date_input("시작일", value=min_date, min_value=min_date, max_value=max_date)
end = st.sidebar.date_input("종료일", value=max_date, min_value=min_date, max_value=max_date)

filtered = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

# ── 요약 지표 ──────────────────────────────────────
total = int(filtered["views"].sum())
avg = filtered["views"].mean()
max_val = int(filtered["views"].max())
max_date_val = filtered.loc[filtered["views"].idxmax(), "date"].strftime("%Y-%m-%d") if not filtered.empty else "-"
recent_7 = int(filtered.tail(7)["views"].sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 조회수", f"{total:,}")
col2.metric("일평균 조회수", f"{avg:.1f}")
col3.metric("최고 조회수", f"{max_val:,}", max_date_val)
col4.metric("최근 7일 조회수", f"{recent_7:,}")

st.divider()

# ── 시계열 차트 ──────────────────────────────────────
st.subheader("일별 조회수 추이")
chart_df = filtered.set_index("date")[["views"]]
st.line_chart(chart_df, use_container_width=True, height=350)

# ── 주간 합계 ──────────────────────────────────────
st.subheader("주간 조회수 합계")
weekly = filtered.copy()
weekly["week"] = weekly["date"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%Y-%m-%d"))
weekly_sum = weekly.groupby("week")["views"].sum().reset_index()
weekly_sum.columns = ["주 시작일", "조회수"]
st.bar_chart(weekly_sum.set_index("주 시작일"), use_container_width=True, height=250)

# ── 데이터 테이블 ──────────────────────────────────────
with st.expander("원본 데이터 보기"):
    table = filtered.copy()
    table["date"] = table["date"].dt.strftime("%Y-%m-%d")
    table.columns = ["날짜", "조회수"]
    table = table.sort_values("날짜", ascending=False).reset_index(drop=True)
    st.dataframe(table, use_container_width=True, height=300)

    csv = table.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("CSV 다운로드", data=csv, file_name="blog_views.csv", mime="text/csv")

# ── 자동 새로고침 ──────────────────────────────────────
st.sidebar.divider()
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()
