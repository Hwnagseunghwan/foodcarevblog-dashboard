#!/usr/bin/env python3
"""
엑셀 과거 데이터 → vola_clicks.json 병합
- vora_history.xlsx의 일별 클릭수를 daily 형식으로 변환
- fdkdbuY 제외
- 엑셀 타이틀을 title 필드에 반영 (snapshots 포함)
"""

import json
import pandas as pd
from pathlib import Path

EXCEL_FILE = "vora_history.xlsx"
CLICKS_FILE = "vola_clicks.json"
EXCLUDE = {"fdkdbuY"}


def main():
    # 엑셀 읽기
    df = pd.read_excel(EXCEL_FILE)
    print(f"엑셀 로드: {len(df)}행")

    # alias 추출 및 제외
    df["alias"] = df["링크"].str.replace("https://vo.la/", "", regex=False).str.strip()
    df = df[~df["alias"].isin(EXCLUDE)]
    print(f"fdkdbuY 제외 후: {len(df)}행")

    # 날짜 컬럼 추출 (링크, 타이틀, alias 제외)
    skip_cols = {"링크", "타이틀", "alias"}
    date_cols = [c for c in df.columns if str(c) not in skip_cols]

    # alias → 타이틀 매핑
    title_map = dict(zip(df["alias"], df["타이틀"].fillna("")))

    # 기존 vola_clicks.json 로드
    if Path(CLICKS_FILE).exists():
        with open(CLICKS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if "daily" not in data:
        data["daily"] = {}
    if "snapshots" not in data:
        data["snapshots"] = {}

    # shorturl 매핑 (snapshots에서 추출)
    shorturl_map = {}
    longurl_map = {}
    for snap_date, snap in data["snapshots"].items():
        for alias, info in snap.items():
            shorturl_map[alias] = info.get("shorturl", f"https://vo.la/{alias}")
            longurl_map[alias] = info.get("longurl", "")

    # 날짜별 daily 데이터 생성
    added_dates = 0
    for col in date_cols:
        # 날짜 문자열 변환
        if hasattr(col, "strftime"):
            date_str = col.strftime("%Y-%m-%d")
        else:
            date_str = str(col).split(" ")[0].strip()

        # 이미 있는 날짜는 덮어쓰지 않음 (API 수집 데이터 우선)
        if date_str in data["daily"]:
            print(f"  [{date_str}] 이미 존재 - 건너뜀")
            continue

        day_data = {}
        for _, row in df.iterrows():
            alias = row["alias"]
            val = row[col]
            if pd.isna(val):
                continue
            try:
                clicks = int(float(val))
            except (ValueError, TypeError):
                continue
            if clicks < 0:
                continue
            day_data[alias] = {
                "title": title_map.get(alias, ""),
                "shorturl": shorturl_map.get(alias, f"https://vo.la/{alias}"),
                "longurl": longurl_map.get(alias, ""),
                "daily_clicks": clicks,
                "total_clicks": 0,  # 과거 누적값 미상 → 0으로 표시
            }

        if day_data:
            data["daily"][date_str] = day_data
            added_dates += 1

    # snapshots의 title도 엑셀 타이틀로 업데이트
    updated_titles = 0
    for snap_date, snap in data["snapshots"].items():
        for alias, info in snap.items():
            if alias in title_map and title_map[alias]:
                info["title"] = title_map[alias]
                updated_titles += 1

    # daily의 기존 날짜 title도 업데이트
    for date_str, day_data in data["daily"].items():
        for alias, info in day_data.items():
            if alias in title_map and title_map[alias]:
                info["title"] = title_map[alias]

    # 날짜 정렬 후 저장
    data["daily"] = dict(sorted(data["daily"].items()))
    with open(CLICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {added_dates}일치 과거 데이터 추가, {updated_titles}개 title 업데이트")
    print(f"저장: {CLICKS_FILE}")
    print(f"\n전체 daily 날짜 목록:")
    for d in sorted(data["daily"].keys()):
        count = len(data["daily"][d])
        total = sum(v["daily_clicks"] for v in data["daily"][d].values())
        print(f"  {d}: {count}개 링크, 총 {total}클릭")


if __name__ == "__main__":
    main()
