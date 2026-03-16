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

# ── 탭3: 일간 현황 ──────────────────────────────────────
with tab3:
    df3 = load_daily_data()

    if df3.empty:
        st.warning("일별 데이터가 없습니다. naver_scraper.py를 먼저 실행해주세요.")
    else:
        recent_14 = df3.tail(14).reset_index(drop=True)
        recent_15 = df3.tail(15).reset_index(drop=True)

        # 일간 조회수 합계 + 증감률 (최근 14일)
        st.subheader("일간 조회수")
        cols = st.columns(len(recent_14))
        for i, row in recent_14.iterrows():
            idx = len(recent_15) - 14 + i
            prev_views = int(recent_15.loc[idx - 1, "views"]) if idx > 0 else None
            curr_views = int(row["views"])
            if prev_views and prev_views > 0:
                rate = (curr_views - prev_views) / prev_views * 100
                delta = f"{rate:+.1f}%"
            else:
                delta = None
            cols[i].metric(row["date"].strftime("%m/%d"), f"{curr_views:,}", delta)

        st.divider()

        # 일간 조회수 추이 차트 (숫자 표시)
        st.subheader("일간 조회수 추이 (최근 14일)")
        recent_14["date_label"] = recent_14["date"].dt.strftime("%m/%d")
        bar_d = alt.Chart(recent_14).mark_bar().encode(
            x=alt.X("date_label:N", sort=None, title="날짜", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("views:Q", title="조회수"),
            tooltip=["date_label", "views"]
        )
        text_d = alt.Chart(recent_14).mark_text(dy=-8, fontSize=11).encode(
            x=alt.X("date_label:N", sort=None),
            y=alt.Y("views:Q"),
            text=alt.Text("views:Q", format=",")
        )
        st.altair_chart(bar_d + text_d, use_container_width=True)

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
