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
    # date: "12. 18" 형식 + year 컬럼으로 실제 날짜 생성
    def parse_date(row):
        try:
            raw = str(row["date"]).replace(" ", "").replace(".", "-").strip("-")
            year = int(row["year"]) if row["year"] else datetime.now().year
            parts = raw.split("-")
            if len(parts) == 2:
                return pd.Timestamp(f"{year}-{int(parts[0]):02d}-{int(parts[1]):02d}")
        except:
            pass
        return pd.NaT

    df["parsed_date"] = df.apply(parse_date, axis=1)
    df["year_month"] = df["parsed_date"].dt.strftime("%Y-%m")
    df["week_label"] = df["parsed_date"].dt.strftime("%Y-W") + df["parsed_date"].dt.isocalendar().week.astype(str).str.zfill(2)

    df["검색량(M)"] = pd.to_numeric(df["검색량(M)"], errors="coerce").fillna(0)
    df["원고비용"] = pd.to_numeric(df["원고비용"], errors="coerce").fillna(0)
    df["작업비용"] = pd.to_numeric(df["작업비용"], errors="coerce").fillna(0)
    df["송출비용"] = pd.to_numeric(df["송출비용"], errors="coerce").fillna(0)
    df["총비용"] = df["원고비용"] + df["작업비용"] + df["송출비용"]
    df["노출여부"] = df["노출여부"].astype(str).str.strip()

    # code 기준 중복 제거 → 원고 송출 단위
    dedup_cols = ["code", "작성자", "브랜드명", "제품명", "소재명", "특이사항",
                  "year", "parsed_date", "year_month", "week_label", "week", "month",
                  "Blog_URL", "원고비용", "작업비용", "송출비용", "총비용", "보라링크1", "보라링크2", "보라링크3"]
    dedup_cols = [c for c in dedup_cols if c in df.columns]
    df_dedup = df.drop_duplicates(subset=["code"])[dedup_cols].copy()

    tab1, tab2, tab5, tab3, tab4 = st.tabs(["📊 현황 요약", "📨 원고 송출량", "🔑 키워드 노출량", "🔍 원고 목록", "💰 비용 분석"])

    # ── 탭2: 원고 송출량 ──────────────────────────────────────
    with tab2:
        total_sent = len(df_dedup)
        df_sent = df_dedup.dropna(subset=["parsed_date"]).copy()

        # code별 키워드 수 / 검색량 합계 계산
        kw_stats = df.groupby("code").agg(
            키워드수=("키워드", "count"),
            검색량합계=("검색량(M)", "sum")
        ).reset_index()
        avg_kw = kw_stats["키워드수"].mean()
        avg_search = kw_stats["검색량합계"].mean()

        # 상단 요약 지표
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("총 원고 송출량", f"{total_sent}건")
        for i, writer in enumerate(sorted(df_dedup["작성자"].dropna().unique())):
            cnt = len(df_dedup[df_dedup["작성자"] == writer])
            [col_s2, col_s3, col_s4][i].metric(f"{writer}", f"{cnt}건")

        st.divider()

        # 원고별 키워드/검색량 요약 테이블
        st.subheader("원고 송출량 키워드 현황")
        col_k1, col_k2 = st.columns(2)
        col_k1.metric("원고당 평균 키워드 수", f"{avg_kw:.1f}개")
        col_k2.metric("원고당 평균 검색량(M) 합계", f"{avg_search:,.0f}")

        # code별 상세 테이블 (dedup 기준 + 키워드 수/검색량 합계 join)
        tbl = df_dedup[["code", "작성자", "브랜드명", "제품명", "parsed_date"]].copy()
        tbl = tbl.merge(kw_stats, on="code", how="left")
        tbl["parsed_date"] = tbl["parsed_date"].dt.strftime("%Y-%m-%d").where(tbl["parsed_date"].notna(), "")
        tbl.columns = ["code", "작성자", "브랜드명", "제품명", "날짜", "키워드 수", "검색량(M) 합계"]
        tbl = tbl.sort_values("날짜", ascending=False).reset_index(drop=True)

        with st.expander("총 원고 송출량 상세 보기"):
            st.dataframe(tbl, use_container_width=True, height=400)
            csv_k = tbl.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv_k, file_name="work_sent_kw.csv", mime="text/csv")

        st.divider()

        # 필터: 작성자 / 브랜드명
        col_f1, col_f2, col_f3 = st.columns(3)
        f_writer = col_f1.selectbox("작성자 필터", ["전체"] + sorted(df_dedup["작성자"].dropna().unique().tolist()), key="sent_writer")
        f_brand  = col_f2.selectbox("브랜드명 필터", ["전체"] + sorted(df_dedup["브랜드명"].dropna().unique().tolist()), key="sent_brand")
        f_view   = col_f3.selectbox("단위", ["월별", "주간별", "일별"], key="sent_view")

        df_f = df_sent.copy()
        if f_writer != "전체":
            df_f = df_f[df_f["작성자"] == f_writer]
        if f_brand != "전체":
            df_f = df_f[df_f["브랜드명"] == f_brand]

        st.divider()

        max_date = df_f["parsed_date"].max()

        if f_view == "월별":
            cutoff = max_date - pd.DateOffset(months=5)
            df_view = df_f[df_f["parsed_date"] >= cutoff.replace(day=1)]
            grp = df_view.groupby(["year_month", "작성자"]).size().reset_index(name="송출량")
            grp_total = df_view.groupby("year_month").size().reset_index(name="송출량").sort_values("year_month")

            st.subheader("월별 원고 송출량 (최근 6개월)")
            bar = alt.Chart(grp.sort_values("year_month")).mark_bar().encode(
                x=alt.X("year_month:N", sort=None, title="월", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("송출량:Q", title="송출량"),
                color=alt.Color("작성자:N", title="작성자"),
                tooltip=["year_month", "작성자", "송출량"]
            )
            text = alt.Chart(grp_total).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("year_month:N", sort=None),
                y=alt.Y("송출량:Q"),
                text=alt.Text("송출량:Q")
            )
            st.altair_chart(bar + text, use_container_width=True)

            st.subheader("월별 브랜드별 송출량 (최근 6개월)")
            grp_brand = df_view.groupby(["year_month", "브랜드명"]).size().reset_index(name="송출량")
            grp_brand_total = df_view.groupby("year_month").size().reset_index(name="송출량").sort_values("year_month")
            bar_b = alt.Chart(grp_brand.sort_values("year_month")).mark_bar().encode(
                x=alt.X("year_month:N", sort=None, title="월", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("송출량:Q", title="송출량"),
                color=alt.Color("브랜드명:N", title="브랜드명"),
                tooltip=["year_month", "브랜드명", "송출량"]
            )
            text_b = alt.Chart(grp_brand_total).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("year_month:N", sort=None),
                y=alt.Y("송출량:Q"),
                text=alt.Text("송출량:Q")
            )
            st.altair_chart(bar_b + text_b, use_container_width=True)

        elif f_view == "주간별":
            cutoff = max_date - pd.Timedelta(days=89)
            df_view = df_f[df_f["parsed_date"] >= cutoff]
            grp = df_view.groupby(["week_label", "작성자"]).size().reset_index(name="송출량")
            grp_total = df_view.groupby("week_label").size().reset_index(name="송출량").sort_values("week_label")

            st.subheader("주간별 원고 송출량 (최근 90일)")
            bar = alt.Chart(grp.sort_values("week_label")).mark_bar().encode(
                x=alt.X("week_label:N", sort=None, title="주차", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("송출량:Q", title="송출량"),
                color=alt.Color("작성자:N", title="작성자"),
                tooltip=["week_label", "작성자", "송출량"]
            )
            text = alt.Chart(grp_total).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("week_label:N", sort=None),
                y=alt.Y("송출량:Q"),
                text=alt.Text("송출량:Q")
            )
            st.altair_chart(bar + text, use_container_width=True)

        else:  # 일별
            cutoff = max_date - pd.Timedelta(days=13)
            df_view = df_f[df_f["parsed_date"] >= cutoff]
            grp = df_view.groupby([df_view["parsed_date"].dt.strftime("%Y-%m-%d"), "작성자"]).size().reset_index(name="송출량")
            grp.columns = ["date", "작성자", "송출량"]
            grp_total = df_view.groupby(df_view["parsed_date"].dt.strftime("%Y-%m-%d")).size().reset_index(name="송출량")
            grp_total.columns = ["date", "송출량"]
            grp_total = grp_total.sort_values("date")

            st.subheader("일별 원고 송출량 (최근 14일)")
            bar = alt.Chart(grp.sort_values("date")).mark_bar().encode(
                x=alt.X("date:N", sort=None, title="날짜", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("송출량:Q", title="송출량"),
                color=alt.Color("작성자:N", title="작성자"),
                tooltip=["date", "작성자", "송출량"]
            )
            text = alt.Chart(grp_total).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("date:N", sort=None),
                y=alt.Y("송출량:Q"),
                text=alt.Text("송출량:Q")
            )
            st.altair_chart(bar + text, use_container_width=True)

        st.divider()

        # 제품명별 송출량
        st.subheader("제품명별 송출량")
        grp_prod = df_f.groupby(["제품명", "브랜드명"]).size().reset_index(name="송출량")
        grp_prod = grp_prod.sort_values("송출량", ascending=False)
        bar_p = alt.Chart(grp_prod).mark_bar().encode(
            x=alt.X("송출량:Q", title="송출량"),
            y=alt.Y("제품명:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)),
            color=alt.Color("브랜드명:N", title="브랜드명"),
            tooltip=["제품명", "브랜드명", "송출량"]
        )
        text_p = alt.Chart(grp_prod).mark_text(dx=5, fontSize=11, align="left").encode(
            x=alt.X("송출량:Q"),
            y=alt.Y("제품명:N", sort="-x"),
            text=alt.Text("송출량:Q")
        )
        st.altair_chart(bar_p + text_p, use_container_width=True)

        st.divider()

        # 원고 송출 원본 테이블
        with st.expander("원고 송출 원본 데이터 보기"):
            show = df_f[["parsed_date", "작성자", "브랜드명", "제품명", "소재명", "Blog_URL", "보라링크1", "보라링크2", "보라링크3"]].copy()
            show["parsed_date"] = show["parsed_date"].dt.strftime("%Y-%m-%d")
            show = show.sort_values("parsed_date", ascending=False).reset_index(drop=True)
            st.dataframe(
                show,
                use_container_width=True,
                height=400,
                column_config={
                    "Blog_URL": st.column_config.LinkColumn("Blog_URL", display_text="🔗 블로그"),
                    "보라링크1": st.column_config.LinkColumn("보라링크1", display_text="🔗 링크1"),
                    "보라링크2": st.column_config.LinkColumn("보라링크2", display_text="🔗 링크2"),
                    "보라링크3": st.column_config.LinkColumn("보라링크3", display_text="🔗 링크3"),
                }
            )
            csv = show.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv, file_name="work_sent.csv", mime="text/csv")

    # ── 탭5: 키워드 노출량 ──────────────────────────────────────
    with tab5:
        # 키워드 기준 전체 데이터 (중복 제거 없음, 유효하지 않은 code 제외)
        df_kw = df.dropna(subset=["parsed_date"]).copy()
        _code_str = df_kw["code"].astype(str).str.strip()
        df_kw = df_kw[~_code_str.isin(["", "nan", "None", "코드없음", "#VALUE!"])]
        df_kw["노출여부"] = df_kw["노출여부"].astype(str).str.strip()
        EXPOSED_VAL = ["O", "o", "Y", "y", "노출", "True", "TRUE", "1", "1.0"]

        total_kw = len(df_kw)
        total_search = df_kw["검색량(M)"].sum()
        df_exposed = df_kw[df_kw["노출여부"].isin(EXPOSED_VAL)]
        exposed_kw = len(df_exposed)
        exposed_search = df_exposed["검색량(M)"].sum()
        exposure_rate_kw = exposed_kw / total_kw * 100 if total_kw > 0 else 0

        # 상단 지표
        col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
        col_k1.metric("총 키워드 수", f"{total_kw:,}개")
        col_k2.metric("총 검색량(M) 합계", f"{total_search:,.0f}")
        col_k3.metric("노출 키워드 수", f"{exposed_kw:,}개")
        col_k4.metric("노출 검색량(M) 합계", f"{exposed_search:,.0f}")
        col_k5.metric("키워드 노출률", f"{exposure_rate_kw:.1f}%")

        st.divider()

        # 필터
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        f_kw_brand   = col_f1.selectbox("브랜드 필터", ["전체"] + sorted(df_kw["브랜드명"].dropna().unique().tolist()), key="kw_brand")
        f_kw_product = col_f2.selectbox("제품 필터", ["전체"] + sorted(df_kw["제품명"].dropna().unique().tolist()), key="kw_product")
        f_kw_exposed = col_f3.selectbox("노출여부 필터", ["전체", "노출", "미노출"], key="kw_exposed")
        f_kw_view    = col_f4.selectbox("단위", ["월별", "주간별", "일별"], key="kw_view")

        df_kf = df_kw.copy()
        if f_kw_brand != "전체":
            df_kf = df_kf[df_kf["브랜드명"] == f_kw_brand]
        if f_kw_product != "전체":
            df_kf = df_kf[df_kf["제품명"] == f_kw_product]
        if f_kw_exposed == "노출":
            df_kf = df_kf[df_kf["노출여부"].isin(EXPOSED_VAL)]
        elif f_kw_exposed == "미노출":
            df_kf = df_kf[~df_kf["노출여부"].isin(EXPOSED_VAL)]

        st.divider()

        max_kw_date = df_kf["parsed_date"].max()

        if f_kw_view == "월별":
            cutoff = max_kw_date - pd.DateOffset(months=5)
            df_kv = df_kf[df_kf["parsed_date"] >= cutoff.replace(day=1)]

            # 키워드 수
            grp_kw = df_kv.groupby(["year_month", "브랜드명"]).agg(
                키워드수=("키워드", "count"),
                검색량합계=("검색량(M)", "sum"),
                노출수=("노출여부", lambda x: x.isin(EXPOSED_VAL).sum())
            ).reset_index()
            grp_kw_total = df_kv.groupby("year_month").agg(
                키워드수=("키워드", "count"),
                검색량합계=("검색량(M)", "sum")
            ).reset_index().sort_values("year_month")
            exposed_grp = df_kv[df_kv["노출여부"].isin(EXPOSED_VAL)].groupby("year_month").agg(
                노출수=("키워드", "count"),
                노출검색량=("검색량(M)", "sum")
            ).reset_index()
            grp_kw_total = grp_kw_total.merge(exposed_grp, on="year_month", how="left").fillna(0)

            st.subheader("월별 키워드 수 (최근 6개월)")
            kw_cmp = grp_kw_total[["year_month", "키워드수", "노출수"]].melt(
                id_vars="year_month", value_vars=["키워드수", "노출수"], var_name="구분", value_name="값"
            )
            kw_cmp["구분"] = kw_cmp["구분"].map({"키워드수": "전체 키워드", "노출수": "노출 키워드"})
            bar_kw = alt.Chart(kw_cmp.sort_values("year_month")).mark_bar().encode(
                x=alt.X("year_month:N", sort=None, title="월", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("값:Q", title="키워드 수"),
                color=alt.Color("구분:N", scale=alt.Scale(domain=["전체 키워드", "노출 키워드"], range=["steelblue", "orange"])),
                xOffset="구분:N",
                tooltip=["year_month", "구분", "값"]
            )
            text_kw = alt.Chart(kw_cmp).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("year_month:N", sort=None),
                xOffset="구분:N",
                y=alt.Y("값:Q"),
                text=alt.Text("값:Q")
            )
            st.altair_chart(bar_kw + text_kw, use_container_width=True)

            st.subheader("월별 검색량(M) 합계 (최근 6개월)")
            sv_cmp = grp_kw_total[["year_month", "검색량합계", "노출검색량"]].melt(
                id_vars="year_month", value_vars=["검색량합계", "노출검색량"], var_name="구분", value_name="값"
            )
            sv_cmp["구분"] = sv_cmp["구분"].map({"검색량합계": "전체 검색량", "노출검색량": "노출 검색량"})
            bar_sv = alt.Chart(sv_cmp.sort_values("year_month")).mark_bar().encode(
                x=alt.X("year_month:N", sort=None, title="월", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("값:Q", title="검색량(M)"),
                color=alt.Color("구분:N", scale=alt.Scale(domain=["전체 검색량", "노출 검색량"], range=["steelblue", "orange"])),
                xOffset="구분:N",
                tooltip=["year_month", "구분", alt.Tooltip("값:Q", format=",")]
            )
            text_sv = alt.Chart(sv_cmp).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("year_month:N", sort=None),
                xOffset="구분:N",
                y=alt.Y("값:Q"),
                text=alt.Text("값:Q", format=",")
            )
            st.altair_chart(bar_sv + text_sv, use_container_width=True)

        elif f_kw_view == "주간별":
            cutoff = max_kw_date - pd.Timedelta(days=89)
            df_kv = df_kf[df_kf["parsed_date"] >= cutoff]

            grp_kw = df_kv.groupby(["week_label", "브랜드명"]).agg(
                키워드수=("키워드", "count"),
                검색량합계=("검색량(M)", "sum"),
                노출수=("노출여부", lambda x: x.isin(EXPOSED_VAL).sum())
            ).reset_index()
            grp_kw_total = df_kv.groupby("week_label").agg(
                키워드수=("키워드", "count"),
                검색량합계=("검색량(M)", "sum")
            ).reset_index().sort_values("week_label")
            exposed_grp = df_kv[df_kv["노출여부"].isin(EXPOSED_VAL)].groupby("week_label").agg(
                노출수=("키워드", "count"),
                노출검색량=("검색량(M)", "sum")
            ).reset_index()
            grp_kw_total = grp_kw_total.merge(exposed_grp, on="week_label", how="left").fillna(0)

            st.subheader("주간별 키워드 수 (최근 90일)")
            kw_cmp = grp_kw_total[["week_label", "키워드수", "노출수"]].melt(
                id_vars="week_label", value_vars=["키워드수", "노출수"], var_name="구분", value_name="값"
            )
            kw_cmp["구분"] = kw_cmp["구분"].map({"키워드수": "전체 키워드", "노출수": "노출 키워드"})
            bar_kw = alt.Chart(kw_cmp.sort_values("week_label")).mark_bar().encode(
                x=alt.X("week_label:N", sort=None, title="주차", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("값:Q", title="키워드 수"),
                color=alt.Color("구분:N", scale=alt.Scale(domain=["전체 키워드", "노출 키워드"], range=["steelblue", "orange"])),
                xOffset="구분:N",
                tooltip=["week_label", "구분", "값"]
            )
            text_kw = alt.Chart(kw_cmp).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("week_label:N", sort=None),
                xOffset="구분:N",
                y=alt.Y("값:Q"),
                text=alt.Text("값:Q")
            )
            st.altair_chart(bar_kw + text_kw, use_container_width=True)

            st.subheader("주간별 검색량(M) 합계 (최근 90일)")
            sv_cmp = grp_kw_total[["week_label", "검색량합계", "노출검색량"]].melt(
                id_vars="week_label", value_vars=["검색량합계", "노출검색량"], var_name="구분", value_name="값"
            )
            sv_cmp["구분"] = sv_cmp["구분"].map({"검색량합계": "전체 검색량", "노출검색량": "노출 검색량"})
            bar_sv = alt.Chart(sv_cmp.sort_values("week_label")).mark_bar().encode(
                x=alt.X("week_label:N", sort=None, title="주차", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("값:Q", title="검색량(M)"),
                color=alt.Color("구분:N", scale=alt.Scale(domain=["전체 검색량", "노출 검색량"], range=["steelblue", "orange"])),
                xOffset="구분:N",
                tooltip=["week_label", "구분", alt.Tooltip("값:Q", format=",")]
            )
            text_sv = alt.Chart(sv_cmp).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("week_label:N", sort=None),
                xOffset="구분:N",
                y=alt.Y("값:Q"),
                text=alt.Text("값:Q", format=",")
            )
            st.altair_chart(bar_sv + text_sv, use_container_width=True)

        else:  # 일별
            cutoff = max_kw_date - pd.Timedelta(days=13)
            df_kv = df_kf[df_kf["parsed_date"] >= cutoff]

            df_kv = df_kv.copy()
            df_kv["date_str"] = df_kv["parsed_date"].dt.strftime("%Y-%m-%d")
            grp_kw = df_kv.groupby(["date_str", "브랜드명"]).agg(
                키워드수=("키워드", "count"),
                검색량합계=("검색량(M)", "sum"),
                노출수=("노출여부", lambda x: x.isin(EXPOSED_VAL).sum())
            ).reset_index()
            grp_kw_total = df_kv.groupby("date_str").agg(
                키워드수=("키워드", "count"),
                검색량합계=("검색량(M)", "sum")
            ).reset_index().sort_values("date_str")
            exposed_grp = df_kv[df_kv["노출여부"].isin(EXPOSED_VAL)].groupby("date_str").agg(
                노출수=("키워드", "count"),
                노출검색량=("검색량(M)", "sum")
            ).reset_index()
            grp_kw_total = grp_kw_total.merge(exposed_grp, on="date_str", how="left").fillna(0)

            st.subheader("일별 키워드 수 (최근 14일)")
            kw_cmp = grp_kw_total[["date_str", "키워드수", "노출수"]].melt(
                id_vars="date_str", value_vars=["키워드수", "노출수"], var_name="구분", value_name="값"
            )
            kw_cmp["구분"] = kw_cmp["구분"].map({"키워드수": "전체 키워드", "노출수": "노출 키워드"})
            bar_kw = alt.Chart(kw_cmp.sort_values("date_str")).mark_bar().encode(
                x=alt.X("date_str:N", sort=None, title="날짜", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("값:Q", title="키워드 수"),
                color=alt.Color("구분:N", scale=alt.Scale(domain=["전체 키워드", "노출 키워드"], range=["steelblue", "orange"])),
                xOffset="구분:N",
                tooltip=["date_str", "구분", "값"]
            )
            text_kw = alt.Chart(kw_cmp).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("date_str:N", sort=None),
                xOffset="구분:N",
                y=alt.Y("값:Q"),
                text=alt.Text("값:Q")
            )
            st.altair_chart(bar_kw + text_kw, use_container_width=True)

            st.subheader("일별 검색량(M) 합계 (최근 14일)")
            sv_cmp = grp_kw_total[["date_str", "검색량합계", "노출검색량"]].melt(
                id_vars="date_str", value_vars=["검색량합계", "노출검색량"], var_name="구분", value_name="값"
            )
            sv_cmp["구분"] = sv_cmp["구분"].map({"검색량합계": "전체 검색량", "노출검색량": "노출 검색량"})
            bar_sv = alt.Chart(sv_cmp.sort_values("date_str")).mark_bar().encode(
                x=alt.X("date_str:N", sort=None, title="날짜", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("값:Q", title="검색량(M)"),
                color=alt.Color("구분:N", scale=alt.Scale(domain=["전체 검색량", "노출 검색량"], range=["steelblue", "orange"])),
                xOffset="구분:N",
                tooltip=["date_str", "구분", alt.Tooltip("값:Q", format=",")]
            )
            text_sv = alt.Chart(sv_cmp).mark_text(dy=-8, fontSize=11).encode(
                x=alt.X("date_str:N", sort=None),
                xOffset="구분:N",
                y=alt.Y("값:Q"),
                text=alt.Text("값:Q", format=",")
            )
            st.altair_chart(bar_sv + text_sv, use_container_width=True)

        st.divider()

        # 제품별 키워드/검색량/노출 현황
        st.subheader("제품별 키워드 현황")
        prod_grp = df_kf.groupby(["제품명", "브랜드명"]).agg(
            키워드수=("키워드", "count"),
            검색량합계=("검색량(M)", "sum"),
            노출수=("노출여부", lambda x: x.isin(EXPOSED_VAL).sum())
        ).reset_index()
        prod_grp["노출률"] = (prod_grp["노출수"] / prod_grp["키워드수"] * 100).round(1)
        prod_grp = prod_grp.sort_values("키워드수", ascending=False).reset_index(drop=True)
        st.dataframe(
            prod_grp,
            use_container_width=True,
            height=min(50 + len(prod_grp) * 35, 400),
            column_config={
                "검색량합계": st.column_config.NumberColumn(format="%,.0f"),
                "노출률": st.column_config.NumberColumn(format="%.1f%%"),
            }
        )

        st.divider()

        # 키워드 원본 데이터
        with st.expander("키워드 원본 데이터 보기"):
            kw_show = df_kf[["parsed_date", "브랜드명", "제품명", "메인/서브", "키워드", "검색량(M)", "노출여부", "최초순위", "Blog_URL"]].copy()
            kw_show["parsed_date"] = kw_show["parsed_date"].dt.strftime("%Y-%m-%d")
            kw_show = kw_show.sort_values("parsed_date", ascending=False).reset_index(drop=True)
            st.dataframe(
                kw_show,
                use_container_width=True,
                height=400,
                column_config={
                    "Blog_URL": st.column_config.LinkColumn("Blog_URL", display_text="🔗 블로그"),
                }
            )
            csv_kw = kw_show.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("CSV 다운로드", data=csv_kw, file_name="keyword_data.csv", mime="text/csv")

    # ── 탭1: 현황 요약 ──────────────────────────────────────
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        total = len(df)
        exposed = len(df[df["노출여부"].isin(["O", "o", "Y", "y", "노출", "True", "TRUE", "1", "1.0"])])
        not_exposed = len(df[df["노출여부"].isin(["X", "x", "N", "n", "미노출", "False", "FALSE"])])
        exposure_rate = exposed / total * 100 if total > 0 else 0

        col1.metric("전체 원고", f"{total}건")
        col2.metric("노출", f"{exposed}건")
        col3.metric("미노출", f"{not_exposed}건")
        col4.metric("노출률", f"{exposure_rate:.1f}%")

        st.divider()

        # 월별 원고 발행 수
        df_dated = df.dropna(subset=["parsed_date"])
        if not df_dated.empty:
            df_dated = df_dated.copy()
            df_dated["year_month"] = df_dated["parsed_date"].dt.strftime("%Y-%m")
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

    # ── 탭3: 원고 목록 ──────────────────────────────────────
    with tab3:
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
            filtered = filtered[filtered["노출여부"].isin(["O", "o", "Y", "y", "노출", "True", "TRUE", "1", "1.0"])]
        elif f_exposed == "미노출":
            filtered = filtered[filtered["노출여부"].isin(["X", "x", "N", "n", "미노출", "False", "FALSE"])]
        if f_keyword:
            filtered = filtered[
                filtered["키워드"].astype(str).str.contains(f_keyword, case=False, na=False) |
                filtered["제목"].astype(str).str.contains(f_keyword, case=False, na=False)
            ]

        st.caption(f"필터 결과: {len(filtered)}건")

        display_cols = ["parsed_date", "메인/서브", "키워드", "원고유형", "제목", "노출여부", "최초순위", "Blog_URL", "보라링크1", "보라링크2", "보라링크3"]
        display_cols = [c for c in display_cols if c in filtered.columns]
        show_df = filtered[display_cols].copy()
        show_df["parsed_date"] = show_df["parsed_date"].dt.strftime("%Y-%m-%d").where(show_df["parsed_date"].notna(), "")

        st.dataframe(
            show_df.sort_values("parsed_date", ascending=False).reset_index(drop=True),
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

    # ── 탭4: 비용 분석 ──────────────────────────────────────
    with tab4:
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        col_c1.metric("총 원고비용", f"{df['원고비용'].sum():,.0f}원")
        col_c2.metric("총 작업비용", f"{df['작업비용'].sum():,.0f}원")
        col_c3.metric("총 송출비용", f"{df['송출비용'].sum():,.0f}원")
        col_c4.metric("총 비용 합계", f"{df['총비용'].sum():,.0f}원")

        st.divider()

        df_cost = df.dropna(subset=["parsed_date"]).copy()
        if not df_cost.empty:
            df_cost["year_month"] = df_cost["parsed_date"].dt.strftime("%Y-%m")
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
