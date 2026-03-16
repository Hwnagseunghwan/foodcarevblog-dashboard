#!/usr/bin/env python3
"""
네이버 블로그 과거 조회수 일괄 수집
- 최근 90일: 일별 데이터 수집
- 90일 이전: 월별 데이터로 보완 (월합계)
실행: python collect_history.py
"""

import os
import json
import asyncio
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

BLOG_ID = os.environ.get("BLOG_ID", "nature_food")
COOKIE_FILE = "naver_cookies.json"
DATA_FILE = "blog_visitors.json"
MONTHLY_FILE = "blog_visitors_monthly.json"

END_DATE = date.today() - timedelta(days=1)
DAILY_START = date.today() - timedelta(days=89)   # 일별: 90일
MONTHLY_START = date(2023, 1, 1)                   # 월별: 2023년부터


async def collect_all():
    daily_data = {}
    monthly_data = {}

    # 기존 데이터 로드
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            daily_data = json.load(f)
        print(f"기존 일별 데이터: {len(daily_data)}일치")

    if Path(MONTHLY_FILE).exists():
        with open(MONTHLY_FILE, encoding="utf-8") as f:
            monthly_data = json.load(f)
        print(f"기존 월별 데이터: {len(monthly_data)}개월치")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        cookie_env = os.environ.get("NAVER_COOKIES")
        if cookie_env:
            await context.add_cookies(json.loads(cookie_env))
        elif Path(COOKIE_FILE).exists():
            with open(COOKIE_FILE) as f:
                await context.add_cookies(json.load(f))

        page = await context.new_page()
        print("\n통계 페이지 접속 중...")
        await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today")
        await asyncio.sleep(5)

        # stat 프레임 찾기
        stat_frame = None
        for frame in page.frames:
            if "blog.stat.naver.com" in frame.url:
                stat_frame = frame
                break

        if not stat_frame:
            print("통계 프레임 없음")
            await browser.close()
            return

        # ── 1. 일별 데이터 수집 (최근 90일) ──────────────
        print(f"\n[1단계] 일별 데이터 수집 ({DAILY_START} ~ {END_DATE})")
        current = END_DATE
        call_count = 0
        while current >= DAILY_START:
            date_str = current.strftime("%Y-%m-%d")
            result = await stat_frame.evaluate(f"""
                async () => {{
                    const url = 'https://blog.stat.naver.com/api/blog/daily/cv?timeDimension=DATE&startDate={date_str}&exclude=&_=' + Date.now();
                    const r = await fetch(url, {{credentials: 'include'}});
                    const d = await r.json();
                    const rows = d?.result?.statDataList?.[0]?.data?.rows || {{}};
                    const result = {{}};
                    (rows.date || []).forEach((d, i) => {{ result[d] = (rows.cv || [])[i]; }});
                    return result;
                }}
            """)
            added = 0
            for d, v in (result or {}).items():
                if DAILY_START.strftime("%Y-%m-%d") <= d <= END_DATE.strftime("%Y-%m-%d"):
                    daily_data[d] = v
                    added += 1
            call_count += 1
            print(f"  {date_str}: +{added}일치 (누적 {len(daily_data)}일)", end="\r")
            current -= timedelta(days=15)
            await asyncio.sleep(0.3)

        print(f"\n  → 일별 {len(daily_data)}일치 수집 완료 ({call_count}번 호출)")

        # ── 2. 월별 데이터 수집 (2023년~) ──────────────
        print(f"\n[2단계] 월별 데이터 수집 ({MONTHLY_START.strftime('%Y-%m')} ~ 현재)")
        current = END_DATE
        call_count = 0
        while current >= MONTHLY_START:
            date_str = current.strftime("%Y-%m-%d")
            result = await stat_frame.evaluate(f"""
                async () => {{
                    const url = 'https://blog.stat.naver.com/api/blog/daily/cv?timeDimension=MONTH&startDate={date_str}&exclude=&_=' + Date.now();
                    const r = await fetch(url, {{credentials: 'include'}});
                    const d = await r.json();
                    const rows = d?.result?.statDataList?.[0]?.data?.rows || {{}};
                    const result = {{}};
                    (rows.date || []).forEach((d, i) => {{ result[d] = (rows.cv || [])[i]; }});
                    return result;
                }}
            """)
            added = 0
            for d, v in (result or {}).items():
                monthly_data[d] = v
                added += 1
            call_count += 1
            if added:
                print(f"  {date_str} 기준: +{added}개월 (누적 {len(monthly_data)}개월)", end="\r")
            # 13개월씩 반환되므로 12개월 뒤로 이동
            current = current.replace(day=1) - timedelta(days=1)
            current = current.replace(day=1) - timedelta(days=365)
            await asyncio.sleep(0.3)

        print(f"\n  → 월별 {len(monthly_data)}개월치 수집 완료 ({call_count}번 호출)")
        await browser.close()

    # 저장
    sorted_daily = dict(sorted(daily_data.items()))
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_daily, f, ensure_ascii=False, indent=2)

    sorted_monthly = dict(sorted(monthly_data.items()))
    with open(MONTHLY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_monthly, f, ensure_ascii=False, indent=2)

    # 결과 요약
    print(f"\n=== 수집 완료 ===")
    print(f"일별: {len(sorted_daily)}일치 ({min(sorted_daily.keys()) if sorted_daily else '-'} ~ {max(sorted_daily.keys()) if sorted_daily else '-'})")
    print(f"월별: {len(sorted_monthly)}개월치 ({min(sorted_monthly.keys()) if sorted_monthly else '-'} ~ {max(sorted_monthly.keys()) if sorted_monthly else '-'})")

    by_year = {}
    for d, v in sorted_monthly.items():
        year = d[:4]
        by_year[year] = by_year.get(year, 0) + v
    print("\n연도별 조회수 (월별 집계):")
    for year, total in sorted(by_year.items()):
        print(f"  {year}년: {total:,}")

    print(f"\n저장: {DATA_FILE}, {MONTHLY_FILE}")


if __name__ == "__main__":
    asyncio.run(collect_all())
