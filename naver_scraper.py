#!/usr/bin/env python3
"""
네이버 블로그 일별 조회수 수집기
- 매일 23:00 실행 (GitHub Actions / Windows 작업 스케줄러)
- 2026-03-01부터 누적 저장
- 데이터: blog_visitors.json
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

NAVER_ID = os.environ.get("NAVER_ID")
NAVER_PW = os.environ.get("NAVER_PW")
BLOG_ID = os.environ.get("BLOG_ID", "nature_food")
COOKIE_FILE = "naver_cookies.json"
DATA_FILE = "blog_visitors.json"
START_DATE = "2026-03-01"


async def load_cookies(context):
    """파일 또는 환경변수(GitHub Secrets)에서 쿠키 로드"""
    # GitHub Actions: 환경변수 NAVER_COOKIES 사용
    cookie_env = os.environ.get("NAVER_COOKIES")
    if cookie_env:
        cookies = json.loads(cookie_env)
        await context.add_cookies(cookies)
        print(f"환경변수에서 쿠키 로드: {len(cookies)}개")
        return True

    # 로컬: 파일에서 로드
    if Path(COOKIE_FILE).exists():
        with open(COOKIE_FILE) as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print(f"파일에서 쿠키 로드: {len(cookies)}개")
        return True

    return False


async def save_cookies(context):
    cookies = await context.cookies()
    with open(COOKIE_FILE, "w") as f:
        json.dump(cookies, f)
    print("쿠키 저장 완료")


async def is_logged_in(page):
    await page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(2)
    login_btn = await page.query_selector(".link_login")
    return login_btn is None


async def login(page, context):
    print("네이버 ID/PW 로그인 시도...")
    await page.goto("https://nid.naver.com/nidlogin.login", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)
    await page.click("#id")
    await page.type("#id", NAVER_ID, delay=80)
    await page.click("#pw")
    await page.type("#pw", NAVER_PW, delay=80)
    await page.click(".btn_login")
    await asyncio.sleep(3)

    if "nidlogin" not in page.url:
        print("로그인 성공")
        await save_cookies(context)
        return True

    print(f"로그인 실패 (현재: {page.url})")
    raise Exception("네이버 로그인 실패 - NAVER_COOKIES 또는 NAVER_ID/NAVER_PW 확인 필요")


async def fetch_stat_api(page, start_date: str) -> dict:
    """통계 API 호출로 조회수 데이터 수집"""
    result = {}

    async def on_response(resp):
        if "blog.stat.naver.com/api/blog/daily/cv" in resp.url:
            try:
                data = await resp.json()
                stat_list = data.get("result", {}).get("statDataList", [])
                if stat_list:
                    rows = stat_list[0].get("data", {}).get("rows", {})
                    dates = rows.get("date", [])
                    counts = rows.get("cv", [])
                    for d, c in zip(dates, counts):
                        result[d] = c
            except Exception as e:
                print(f"API 파싱 오류: {e}")

    page.on("response", on_response)
    await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today")
    await asyncio.sleep(5)
    page.remove_listener("response", on_response)
    return result


def load_existing_data() -> dict:
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(existing: dict, new_data: dict) -> dict:
    merged = {**existing, **new_data}
    sorted_data = dict(sorted(merged.items()))
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
    return sorted_data


def print_summary(data: dict):
    print("\n=== 수집 결과 ===")
    recent = {k: v for k, v in data.items() if k >= START_DATE}
    for date, count in sorted(recent.items())[-15:]:
        bar = "█" * min(int(count / 10), 30) if count > 0 else ""
        print(f"  {date}: {count:>6,} {bar}")
    print(f"\n총 {len(recent)}일치 데이터 (합계: {sum(recent.values()):,} 조회수)")


async def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 네이버 블로그 조회수 수집 시작")
    print(f"수집 기간: {START_DATE} ~ {yesterday}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        cookie_loaded = await load_cookies(context)
        if cookie_loaded and await is_logged_in(page):
            print("쿠키 로그인 유지")
        else:
            await login(page, context)

        print("조회수 데이터 수집 중...")
        new_data = await fetch_stat_api(page, START_DATE)
        await browser.close()

    if not new_data:
        print("데이터 수집 실패")
        return

    new_data = {k: v for k, v in new_data.items() if k <= yesterday}
    existing = load_existing_data()
    merged = save_data(existing, new_data)
    print_summary(merged)
    print(f"\n저장 완료: {DATA_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
