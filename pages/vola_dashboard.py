#!/usr/bin/env python3
"""
VOLA 단축URL 클릭수 대시보드
실행: streamlit run dashboard.py (멀티페이지 자동 인식)
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

VOLA_FILE = "vola_clicks.json"

st.set_page_config(
    page_title="VOLA 클릭수 대시보드",
    page_icon="🔗",
    layout="wide"
)

require_login()

# 자동 생성 사이드바 네비게이션 숨기고 커스텀 링크로 교체
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

st.markdown("<a id='vola-dashboard'></a>", unsafe_allow_html=True)
st.title("🔗 VOLA 단축URL 클릭수 대시보드")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


@st.cache_data(ttl=300)
def load_vola_data():
    if not Path(VOLA_FILE).exists():
        return {}
    with open(VOLA_FILE, encoding="utf-8") as f:
        return json.load(f)


vola = load_vola_data()
daily_vola = vola.get("daily", {})

if not daily_vola:
    st.warning("VOLA 데이터가 없습니다. vola_scraper.py를 먼저 실행해주세요.")
else:
    all_dates = sorted(daily_vola.keys())

    # longurl에서 의미있는 레이블 생성
    def label_from_longurl(longurl, alias):
        import re
        if "/event/eventDetail/" in longurl:
            m = re.search(r"/eventDetail/(\d+)", longurl)
            return f"이벤트 #{m.group(1)}" if m else f"이벤트 ({alias})"
        if "/shop/mealPlan/E/" in longurl:
            m = re.search(r"/mealPlan/E/(\d+)", longurl)
            return f"식단플랜(E) #{m.group(1)}" if m else f"식단플랜(E) ({alias})"
        if "/shop/mealPlan/U/" in longurl:
            m = re.search(r"/mealPlan/U/(\d+)", longurl)
            return f"식단플랜(U) #{m.group(1)}" if m else f"식단플랜(U) ({alias})"
        if "/shop/goodsView/" in longurl:
            m = re.search(r"/goodsView/0*(\d+)", longurl)
            return f"상품 #{m.group(1)}" if m else f"상품 ({alias})"
        return alias

    # 링크 메타 정보 수집 (가장 최근 날짜 기준 우선)
    title_map = {}
    shorturl_map = {}
    longurl_map = {}
    created_at_map = {}
    for d in all_dates:
        for alias, info in daily_vola[d].items():
            raw_title = info.get("title", "") or ""
            # 깨진 문자 포함 시 빈 문자열 처리
            if "\ufffd" in raw_title:
                raw_title = ""
            title_map[alias] = raw_title
            shorturl_map[alias] = info.get("shorturl", f"https://vo.la/{alias}")
            longurl_map[alias] = info.get("longurl", "")
            created_at_map[alias] = info.get("created_at", "")

    # snapshot에서 created_at 보완
    for snap in vola.get("snapshots", {}).values():
        for alias, info in snap.items():
            if alias not in created_at_map or not created_at_map[alias]:
                created_at_map[alias] = info.get("created_at", "")

    # URL 경로 기반 카테고리 분류
    def categorize(longurl):
        if "/event/eventDetail/" in longurl:
            return "이벤트"
        if "/shop/mealPlan/E/" in longurl:
            return "식단플랜(E)"
        if "/shop/mealPlan/U/" in longurl:
            return "식단플랜(U)"
        if "/shop/goodsView/" in longurl:
            return "상품"
        return "기타"

    # 타이틀이 없으면 longurl 기반 레이블 사용
    for alias in list(title_map.keys()):
        if not title_map[alias]:
            title_map[alias] = label_from_longurl(longurl_map.get(alias, ""), alias)

    # 전체 데이터 → 롱 포맷
    rows = []
    for d in all_dates:
        for alias, info in daily_vola[d].items():
            rows.append({
                "date": d,
                "alias": alias,
                "title": title_map.get(alias, alias),
                "shorturl": shorturl_map.get(alias, ""),
                "longurl": longurl_map.get(alias, ""),
                "category": categorize(longurl_map.get(alias, "")),
                "created_at": created_at_map.get(alias, ""),
                "daily_clicks": info.get("daily_clicks", 0),
                "total_clicks": info.get("total_clicks", 0),
            })
    df_all = pd.DataFrame(rows)
    df_all["date"] = pd.to_datetime(df_all["date"])

    # 탭 구성
    tab2, tab1, tab3 = st.tabs(["🔗 링크별 현황", "📋 일별 현황 (최근 14일)", "📊 전체 데이터"])

    # ── 탭1: 일별 현황 ──────────────────────────────────────
    with tab1:
        # 시작일 선택 반영
        date_options = sorted(df_all["date"].dt.strftime("%Y-%m-%d").unique().tolist())
        default_start = "2026-03-18"
        daily_start = st.session_state.get("vola_daily_start", default_start)

        recent_dates = [d for d in date_options if d >= daily_start][:14]
        df_recent = df_all[df_all["date"].dt.strftime("%Y-%m-%d").isin(recent_dates)]

        # 일별 총 클릭
        daily_total = df_recent.groupby(df_recent["date"].dt.strftime("%Y-%m-%d"))["daily_clicks"].sum().reset_index()
        daily_total.columns = ["date", "total_clicks"]
        daily_total = daily_total.sort_values("date")

        st.subheader(f"일별 총 클릭수 ({daily_start} ~)")
        cols = st.columns(len(recent_dates))
        for i, d in enumerate(recent_dates):
            row = daily_total[daily_total["date"] == d]
            total = int(row["total_clicks"].values[0]) if len(row) > 0 else 0
            prev_d = recent_dates[i - 1] if i > 0 else None
            prev_row = daily_total[daily_total["date"] == prev_d] if prev_d else None
            prev_total = int(prev_row["total_clicks"].values[0]) if prev_row is not None and len(prev_row) > 0 else None
            delta = f"{(total - prev_total) / prev_total * 100:+.1f}%" if prev_total and prev_total > 0 else None
            cols[i].metric(d[5:], f"{total:,}", delta)

        st.divider()

        # 일별 총 클릭 차트
        st.subheader(f"일별 총 클릭수 추이 ({daily_start} ~)")
        bar_d = alt.Chart(daily_total).mark_bar().encode(
            x=alt.X("date:N", sort=None, title="날짜", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("total_clicks:Q", title="클릭수"),
            tooltip=["date", "total_clicks"]
        )
        text_d = alt.Chart(daily_total).mark_text(dy=-8, fontSize=11).encode(
            x=alt.X("date:N", sort=None),
            y=alt.Y("total_clicks:Q"),
            text=alt.Text("total_clicks:Q", format=",")
        )
        st.altair_chart(bar_d + text_d, use_container_width=True)

        st.divider()

        # 카테고리별 일별 클릭 스택 차트
        st.subheader(f"카테고리별 일별 클릭수 ({daily_start} ~)")
        cat_daily = df_recent.groupby([df_recent["date"].dt.strftime("%Y-%m-%d"), "category"])["daily_clicks"].sum().reset_index()
        cat_daily.columns = ["date", "category", "clicks"]
        bar_cat = alt.Chart(cat_daily).mark_bar().encode(
            x=alt.X("date:N", sort=None, title="날짜", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("clicks:Q", title="클릭수"),
            color=alt.Color("category:N", title="카테고리"),
            tooltip=["date", "category", "clicks"]
        )
        st.altair_chart(bar_cat, use_container_width=True)

        st.divider()

        # 일별 원본 데이터
        with st.expander("일별 원본 데이터 보기"):
            pivot = df_recent.pivot_table(index=["alias", "title", "category"], columns=df_recent["date"].dt.strftime("%Y-%m-%d"), values="daily_clicks", fill_value=0).reset_index()
            pivot.columns.name = None
            st.dataframe(pivot, use_container_width=True, height=400)
            csv_d = pivot.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv_d, file_name="vola_daily.csv", mime="text/csv")

        st.divider()

        # 시작일 선택 폼
        with st.form("vola_daily_selector"):
            col1, col2 = st.columns([2, 1])
            _sel = st.session_state.get("vola_daily_start", default_start)
            _sel_idx = date_options.index(_sel) if _sel in date_options else next((i for i, d in enumerate(date_options) if d >= _sel), 0)
            selected = col1.selectbox(
                "📋 일별 현황 시작일 선택",
                options=date_options,
                index=_sel_idx,
                help="선택한 날부터 이후 14일을 위 차트에 표시합니다."
            )
            col2.markdown("<br>", unsafe_allow_html=True)
            submitted = col2.form_submit_button("적용", use_container_width=True)
        if "vola_daily_start" not in st.session_state or submitted:
            st.session_state["vola_daily_start"] = selected
            if submitted:
                st.rerun()

    # ── 탭2: 링크별 현황 ──────────────────────────────────────
    with tab2:
        # 기간 선택
        period_options = ["최근 7일", "최근 14일", "최근 30일", "전체"]
        selected_period = st.session_state.get("vola_link_period", "최근 14일")

        today = df_all["date"].max()
        period_map = {
            "최근 7일": today - pd.Timedelta(days=6),
            "최근 14일": today - pd.Timedelta(days=13),
            "최근 30일": today - pd.Timedelta(days=29),
            "전체": df_all["date"].min(),
        }
        df_period = df_all[df_all["date"] >= period_map[selected_period]]

        # 링크별 합계
        link_total = df_period.groupby(["alias", "title", "category", "shorturl", "longurl", "created_at"])["daily_clicks"].sum().reset_index()
        link_total.columns = ["alias", "title", "category", "shorturl", "longurl", "created_at", "clicks"]
        link_total = link_total.sort_values("clicks", ascending=False).reset_index(drop=True)
        # 차트용 레이블: 타이틀 (개설일)
        link_total["title_label"] = link_total.apply(
            lambda r: f"{r['title']} ({r['created_at']})" if r['created_at'] else r['title'], axis=1
        )

        st.subheader(f"링크별 클릭수 합계 ({selected_period})")

        # 카테고리 필터
        all_cats = ["전체"] + sorted(link_total["category"].unique().tolist())
        col_f1, col_f2 = st.columns([3, 1])
        cat_filter = col_f1.selectbox("카테고리 필터", all_cats)
        if cat_filter != "전체":
            link_filtered = link_total[link_total["category"] == cat_filter]
        else:
            link_filtered = link_total

        bar_l = alt.Chart(link_filtered.head(20)).mark_bar().encode(
            x=alt.X("clicks:Q", title="클릭수"),
            y=alt.Y("title_label:N", sort="-x", title=None,
                    axis=alt.Axis(labelLimit=500, labelFontSize=12)),
            color=alt.Color("category:N", title="카테고리"),
            tooltip=["title_label", "category", "clicks", "shorturl"]
        )
        text_l = alt.Chart(link_filtered.head(20)).mark_text(dx=5, fontSize=11, align="left").encode(
            x=alt.X("clicks:Q"),
            y=alt.Y("title_label:N", sort="-x"),
            text=alt.Text("clicks:Q", format=",")
        )
        st.altair_chart(bar_l + text_l, use_container_width=True)

        st.divider()

        # 링크 테이블 (클릭 가능한 링크 포함)
        display_df = link_filtered[["title", "created_at", "category", "clicks", "shorturl", "longurl"]].copy()
        display_df.columns = ["타이틀", "개설일", "카테고리", f"클릭수({selected_period})", "단축URL", "원본URL"]
        st.dataframe(
            display_df,
            use_container_width=True,
            height=min(50 + len(display_df) * 35, 500),
            column_config={
                "단축URL": st.column_config.LinkColumn("단축URL", display_text="🔗 링크"),
                "원본URL": st.column_config.LinkColumn("원본URL", display_text="🌐 이동"),
            }
        )

        with st.expander("CSV 다운로드"):
            csv_l = display_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv_l, file_name="vola_links.csv", mime="text/csv")

        st.divider()

        # 기간 선택 폼
        with st.form("vola_period_selector"):
            col_p1, col_p2 = st.columns([2, 1])
            selected_p = col_p1.selectbox(
                "📅 조회 기간 선택",
                options=period_options,
                index=period_options.index(st.session_state.get("vola_link_period", "최근 14일"))
            )
            col_p2.markdown("<br>", unsafe_allow_html=True)
            submitted_p = col_p2.form_submit_button("적용", use_container_width=True)
        if "vola_link_period" not in st.session_state or submitted_p:
            st.session_state["vola_link_period"] = selected_p
            if submitted_p:
                st.rerun()

    # ── 탭3: 전체 데이터 ──────────────────────────────────────
    with tab3:
        st.subheader("전체 일별 클릭 데이터")

        # 누적 총 클릭 (가장 최근 snapshot 기준)
        snapshots = vola.get("snapshots", {})
        if snapshots:
            latest_snap = snapshots[max(snapshots.keys())]
            total_all = sum(v.get("total_clicks", 0) for v in latest_snap.values())
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("전체 링크 수", f"{len(latest_snap)}개")
            col_s2.metric("전체 누적 클릭수", f"{total_all:,}")
            col_s3.metric("수집 기간", f"{len(all_dates)}일")
            st.divider()

        # 전체 날짜별 총 클릭 테이블
        all_daily_total = df_all.groupby(df_all["date"].dt.strftime("%Y-%m-%d"))["daily_clicks"].sum().reset_index()
        all_daily_total.columns = ["날짜", "총 클릭수"]
        all_daily_total = all_daily_total.sort_values("날짜", ascending=False).reset_index(drop=True)
        st.dataframe(all_daily_total, use_container_width=True, height=400)

        csv_all = all_daily_total.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("전체 CSV 다운로드", data=csv_all, file_name="vola_all.csv", mime="text/csv")


# ── 사이드바 ──────────────────────────────────────
st.sidebar.divider()
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

show_user_sidebar()

st.sidebar.divider()
st.sidebar.link_button("🔄 전체 데이터 재수집", "https://github.com/Hwnagseunghwan/foodcarevblog-dashboard/actions/workflows/scraper.yml", use_container_width=True)
st.sidebar.caption("클릭 후 'Run workflow' → 3분 후 데이터 새로고침")
