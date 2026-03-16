#!/usr/bin/env python3
"""
Cle 공식블로그 업무 대시보드
"""

import json
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
from datetime import datetime

DATA_FILE = "work_data.json"

st.set_page_config(
    page_title="Work Dashboard",
    page_icon="📋",
    layout="wide"
)

# 사이드바 커스텀 네비게이션
st.markdown("""
<style>[data-testid="stSidebarNav"] { display: none; }</style>
""", unsafe_allow_html=True)
st.sidebar.page_link("dashboard.py", label="📊 Cle Blog Dashboard")
st.sidebar.page_link("pages/vola_dashboard.py", label="🔗 Vola Dashboard")
st.sidebar.page_link("pages/work_dashboard.py", label="📋 Work Dashboard")
st.sidebar.divider()
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.markdown("<a id='work-dashboard'></a>", unsafe_allow_html=True)
st.title("📋 Work Dashboard")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    if not Path(DATA_FILE).exists():
        return pd.DataFrame()
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw["rows"])
    updated_at = raw.get("updated_at", "")
    return df, updated_at


result = load_data()
if isinstance(result, pd.DataFrame):
    df = result
    updated_at = ""
else:
    df, updated_at = result

if df.empty:
    st.warning("데이터가 없습니다. sheets_scraper.py를 먼저 실행해주세요.")
else:
    st.caption(f"마지막 업데이트: {updated_at}  |  전체 {len(df)}건")

    # 전처리
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["검색량(M)"] = pd.to_numeric(df["검색량(M)"], errors="coerce").fillna(0)
    df["원고비용"] = pd.to_numeric(df["원고비용"], errors="coerce").fillna(0)
    df["작업비용"] = pd.to_numeric(df["작업비용"], errors="coerce").fillna(0)
    df["송출비용"] = pd.to_numeric(df["송출비용"], errors="coerce").fillna(0)
    df["총비용"] = df["원고비용"] + df["작업비용"] + df["송출비용"]
    df["노출여부"] = df["노출여부"].astype(str).str.strip()

    tab1, tab2, tab3 = st.tabs(["📊 현황 요약", "🔍 원고 목록", "💰 비용 분석"])

    # ── 탭1: 현황 요약 ──────────────────────────────────────
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        total = len(df)
        exposed = len(df[df["노출여부"].isin(["O", "o", "Y", "y", "노출", "True", "TRUE"])])
        not_exposed = len(df[df["노출여부"].isin(["X", "x", "N", "n", "미노출", "False", "FALSE"])])
        exposure_rate = exposed / total * 100 if total > 0 else 0

        col1.metric("전체 원고", f"{total}건")
        col2.metric("노출", f"{exposed}건")
        col3.metric("미노출", f"{not_exposed}건")
        col4.metric("노출률", f"{exposure_rate:.1f}%")

        st.divider()

        # 월별 원고 발행 수
        df_dated = df.dropna(subset=["date"])
        if not df_dated.empty:
            df_dated = df_dated.copy()
            df_dated["year_month"] = df_dated["date"].dt.strftime("%Y-%m")
            monthly = df_dated.groupby("year_month").size().reset_index(name="건수")
            monthly = monthly.sort_values("year_month")

            st.subheader("월별 원고 발행 수")
            bar_m = alt.Chart(monthly.tail(12)).mark_bar().encode(
                x=alt.X("year_month:N", sort=None, title="월", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("건수:Q", title="건수"),
                tooltip=["year_month", "건수"]
            )
            text_m = alt.Chart(monthly.tail(12)).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("year_month:N", sort=None),
                y=alt.Y("건수:Q"),
                text=alt.Text("건수:Q")
            )
            st.altair_chart(bar_m + text_m, use_container_width=True)

        st.divider()

        # 원고유형별 / 노출여부별 분포
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("원고유형별 분포")
            type_cnt = df["원고유형"].value_counts().reset_index()
            type_cnt.columns = ["원고유형", "건수"]
            bar_t = alt.Chart(type_cnt).mark_bar().encode(
                x=alt.X("건수:Q", title="건수"),
                y=alt.Y("원고유형:N", sort="-x", title=None),
                tooltip=["원고유형", "건수"]
            )
            text_t = alt.Chart(type_cnt).mark_text(dx=5, fontSize=11, align="left").encode(
                x=alt.X("건수:Q"),
                y=alt.Y("원고유형:N", sort="-x"),
                text=alt.Text("건수:Q")
            )
            st.altair_chart(bar_t + text_t, use_container_width=True)

        with col_b:
            st.subheader("메인/서브 분포")
            ms_cnt = df["메인/서브"].value_counts().reset_index()
            ms_cnt.columns = ["구분", "건수"]
            pie = alt.Chart(ms_cnt).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("건수:Q"),
                color=alt.Color("구분:N"),
                tooltip=["구분", "건수"]
            )
            st.altair_chart(pie, use_container_width=True)

    # ── 탭2: 원고 목록 ──────────────────────────────────────
    with tab2:
        # 필터
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        f_type = col_f1.selectbox("원고유형", ["전체"] + sorted(df["원고유형"].dropna().unique().tolist()))
        f_ms = col_f2.selectbox("메인/서브", ["전체"] + sorted(df["메인/서브"].dropna().unique().tolist()))
        f_exposed = col_f3.selectbox("노출여부", ["전체", "노출", "미노출"])
        f_keyword = col_f4.text_input("키워드 검색")

        filtered = df.copy()
        if f_type != "전체":
            filtered = filtered[filtered["원고유형"] == f_type]
        if f_ms != "전체":
            filtered = filtered[filtered["메인/서브"] == f_ms]
        if f_exposed == "노출":
            filtered = filtered[filtered["노출여부"].isin(["O", "o", "Y", "y", "노출", "True", "TRUE"])]
        elif f_exposed == "미노출":
            filtered = filtered[filtered["노출여부"].isin(["X", "x", "N", "n", "미노출", "False", "FALSE"])]
        if f_keyword:
            filtered = filtered[
                filtered["키워드"].astype(str).str.contains(f_keyword, case=False, na=False) |
                filtered["제목"].astype(str).str.contains(f_keyword, case=False, na=False)
            ]

        st.caption(f"필터 결과: {len(filtered)}건")

        display_cols = ["date", "메인/서브", "키워드", "원고유형", "제목", "노출여부", "최초순위", "Blog_URL", "보라링크1", "보라링크2", "보라링크3"]
        display_cols = [c for c in display_cols if c in filtered.columns]
        show_df = filtered[display_cols].copy()
        show_df["date"] = show_df["date"].dt.strftime("%Y-%m-%d").where(show_df["date"].notna(), "")

        st.dataframe(
            show_df.sort_values("date", ascending=False).reset_index(drop=True),
            use_container_width=True,
            height=500,
            column_config={
                "Blog_URL": st.column_config.LinkColumn("Blog_URL", display_text="🔗 블로그"),
                "보라링크1": st.column_config.LinkColumn("보라링크1", display_text="🔗 링크1"),
                "보라링크2": st.column_config.LinkColumn("보라링크2", display_text="🔗 링크2"),
                "보라링크3": st.column_config.LinkColumn("보라링크3", display_text="🔗 링크3"),
            }
        )

        csv = filtered.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("CSV 다운로드", data=csv, file_name="work_data.csv", mime="text/csv")

    # ── 탭3: 비용 분석 ──────────────────────────────────────
    with tab3:
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        col_c1.metric("총 원고비용", f"{df['원고비용'].sum():,.0f}원")
        col_c2.metric("총 작업비용", f"{df['작업비용'].sum():,.0f}원")
        col_c3.metric("총 송출비용", f"{df['송출비용'].sum():,.0f}원")
        col_c4.metric("총 비용 합계", f"{df['총비용'].sum():,.0f}원")

        st.divider()

        df_cost = df.dropna(subset=["date"]).copy()
        if not df_cost.empty:
            df_cost["year_month"] = df_cost["date"].dt.strftime("%Y-%m")
            cost_monthly = df_cost.groupby("year_month")[["원고비용", "작업비용", "송출비용"]].sum().reset_index()
            cost_monthly = cost_monthly.sort_values("year_month").tail(12)
            cost_melted = cost_monthly.melt(id_vars="year_month", var_name="비용유형", value_name="금액")

            st.subheader("월별 비용 현황")
            bar_c = alt.Chart(cost_melted).mark_bar().encode(
                x=alt.X("year_month:N", sort=None, title="월", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("금액:Q", title="금액(원)"),
                color=alt.Color("비용유형:N", title="비용유형"),
                tooltip=["year_month", "비용유형", "금액"]
            )
            st.altair_chart(bar_c, use_container_width=True)

        st.divider()

        st.subheader("원고유형별 비용 합계")
        cost_type = df.groupby("원고유형")[["원고비용", "작업비용", "송출비용", "총비용"]].sum().reset_index()
        cost_type = cost_type.sort_values("총비용", ascending=False)
        st.dataframe(
            cost_type,
            use_container_width=True,
            column_config={
                "원고비용": st.column_config.NumberColumn(format="%,.0f원"),
                "작업비용": st.column_config.NumberColumn(format="%,.0f원"),
                "송출비용": st.column_config.NumberColumn(format="%,.0f원"),
                "총비용": st.column_config.NumberColumn(format="%,.0f원"),
            }
        )
