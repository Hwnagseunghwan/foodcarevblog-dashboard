#!/usr/bin/env python3
"""
VOLA 단축URL 일별 클릭수 수집기
- 매일 전체 링크 누적 클릭수 수집
- 전일 대비 차이로 일별 클릭수 계산
- 데이터: vola_clicks.json
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

VOLA_API_KEY = os.environ.get("VOLA_API_KEY")
CLICKS_FILE = "vola_clicks.json"
BASE_URL = "https://vo.la/api"


def fetch_all_links() -> list:
    """전체 링크 목록 수집 (페이지네이션)"""
    headers = {
        "Authorization": f"Bearer {VOLA_API_KEY}",
        "Content-Type": "application/json"
    }
    all_links = []
    page = 1
    while True:
        resp = requests.get(f"{BASE_URL}/urls?limit=100&page={page}&order=date", headers=headers)
        data = resp.json()
        if data.get("error") != 0:
            print(f"API 오류: {data.get('message')}")
            break
        urls = data["data"]["urls"]
        all_links.extend(urls)
        if page >= data["data"]["maxpage"]:
            break
        page += 1
    return all_links


def load_existing() -> dict:
    if Path(CLICKS_FILE).exists():
        with open(CLICKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(CLICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if not VOLA_API_KEY:
        print("VOLA_API_KEY가 설정되지 않았습니다.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] VOLA 클릭수 수집 시작")

    # 전체 링크 수집
    links = fetch_all_links()
    print(f"총 {len(links)}개 링크 수집")

    # 오늘 스냅샷 (누적 클릭수)
    snapshot = {}
    for link in links:
        alias = link["alias"]
        snapshot[alias] = {
            "id": link["id"],
            "shorturl": link["shorturl"],
            "longurl": link["longurl"],
            "title": link.get("title") or "",
            "total_clicks": link["clicks"],
            "created_at": link.get("date", "")[:10],
        }

    # 기존 데이터 로드
    existing = load_existing()

    # 일별 클릭수 계산 (오늘 누적 - 어제 누적)
    daily_clicks = {}
    prev_snapshot = existing.get("snapshots", {}).get(yesterday, {})
    for alias, info in snapshot.items():
        prev_total = prev_snapshot.get(alias, {}).get("total_clicks", 0)
        daily = max(0, info["total_clicks"] - prev_total)
        daily_clicks[alias] = {
            "title": info["title"],
            "shorturl": info["shorturl"],
            "longurl": info["longurl"],
            "created_at": info.get("created_at", ""),
            "daily_clicks": daily,
            "total_clicks": info["total_clicks"],
        }

    # 데이터 구조 업데이트
    if "snapshots" not in existing:
        existing["snapshots"] = {}
    if "daily" not in existing:
        existing["daily"] = {}

    existing["snapshots"][today] = snapshot
    existing["daily"][today] = daily_clicks

    save_data(existing)

    # 결과 출력
    print(f"\n=== {today} 클릭 현황 ===")
    sorted_links = sorted(daily_clicks.items(), key=lambda x: x[1]["daily_clicks"], reverse=True)
    for alias, info in sorted_links:
        if info["total_clicks"] > 0:
            print(f"  {alias} | 일별: +{info['daily_clicks']} | 누적: {info['total_clicks']} | {info['title'][:25]}")
    total_daily = sum(v["daily_clicks"] for v in daily_clicks.values())
    total_all = sum(v["total_clicks"] for v in daily_clicks.values())
    print(f"\n오늘 총 클릭: {total_daily} | 전체 누적: {total_all}")
    print(f"\n저장 완료: {CLICKS_FILE}")


if __name__ == "__main__":
    main()
