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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

NAVER_ID = os.environ.get("NAVER_ID")
NAVER_PW = os.environ.get("NAVER_PW")
BLOG_ID = os.environ.get("BLOG_ID", "nature_food")
COOKIE_FILE = "naver_cookies.json"
DATA_FILE = "blog_visitors.json"
MONTHLY_FILE = "blog_visitors_monthly.json"
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
    """admin.blog.naver.com 접근 가능 여부로 실제 로그인 상태 확인"""
    await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(2)
    return "nidlogin" not in page.url


async def login(page, context):
    if not NAVER_ID or not NAVER_PW:
        raise Exception(
            "쿠키 만료 + NAVER_ID/NAVER_PW 미설정\n"
            "해결방법:\n"
            "  [로컬] naver_cookies.json을 최신 쿠키로 갱신하거나 .env에 NAVER_ID/NAVER_PW 설정\n"
            "  [GitHub Actions] NAVER_COOKIES 시크릿을 최신 쿠키로 갱신"
        )
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
    await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today", timeout=30000)
    await asyncio.sleep(2)

    if "nidlogin" in page.url:
        page.remove_listener("response", on_response)
        print("⚠ admin 블로그 세션 만료 — 쿠키를 갱신하거나 NAVER_ID/NAVER_PW를 설정하세요")
        return {}

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


async def fetch_monthly_api(page) -> dict:
    """stat 프레임에서 최근 3개월 월별 데이터 수집"""
    stat_frame = None
    for frame in page.frames:
        if "blog.stat.naver.com" in frame.url:
            stat_frame = frame
            break

    if not stat_frame:
        print("stat 프레임 없음 - 월별 수집 건너뜀")
        return {}

    result = {}
    today = datetime.now()
    # 최근 3개월치 커버 (현재월 포함, 이전 2개월)
    for months_ago in range(3):
        if months_ago == 0:
            date_str = today.strftime("%Y-%m-%d")
        else:
            # 이전 달 1일로 이동
            d = today.replace(day=1)
            for _ in range(months_ago):
                d = (d - timedelta(days=1)).replace(day=1)
            date_str = d.strftime("%Y-%m-%d")

        data = await stat_frame.evaluate(f"""
            async () => {{
                const url = 'https://blog.stat.naver.com/api/blog/daily/cv?timeDimension=MONTH&startDate={date_str}&exclude=&_=' + Date.now();
                const r = await fetch(url, {{credentials: 'include'}});
                const d = await r.json();
                const rows = d?.result?.statDataList?.[0]?.data?.rows || {{}};
                const res = {{}};
                (rows.date || []).forEach((d, i) => {{ res[d] = (rows.cv || [])[i]; }});
                return res;
            }}
        """)
        for d, v in (data or {}).items():
            result[d] = v
        await asyncio.sleep(0.5)

    return result


def load_monthly_data() -> dict:
    if Path(MONTHLY_FILE).exists():
        with open(MONTHLY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_monthly_data(existing: dict, new_data: dict) -> dict:
    merged = {**existing, **new_data}
    sorted_data = dict(sorted(merged.items()))
    with open(MONTHLY_FILE, "w", encoding="utf-8") as f:
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
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    yesterday = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n[{now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST] 네이버 블로그 조회수 수집 시작")
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

        print("일별 조회수 데이터 수집 중...")
        new_data = await fetch_stat_api(page, START_DATE)

        print("월별 조회수 데이터 수집 중...")
        new_monthly = await fetch_monthly_api(page)
        await browser.close()

    if not new_data:
        print("일별 데이터 수집 실패")
        return

    # 일별 저장
    new_data = {k: v for k, v in new_data.items() if k <= yesterday}
    existing = load_existing_data()
    merged = save_data(existing, new_data)
    print_summary(merged)
    print(f"\n일별 저장 완료: {DATA_FILE}")

    # 월별 저장
    if new_monthly:
        existing_monthly = load_monthly_data()
        merged_monthly = save_monthly_data(existing_monthly, new_monthly)
        print(f"월별 저장 완료: {MONTHLY_FILE} ({len(merged_monthly)}개월치)")


if __name__ == "__main__":
    asyncio.run(main())
