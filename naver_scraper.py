#!/usr/bin/env python3
"""
네이버 블로그 일별 조회수 수집기
- Playwright ID/PW 직접 로그인 방식 (쿠키 의존 없음)
- 로컬 PC(한국 IP)에서 매일 실행 → 네이버 IP 신뢰 환경에서만 동작
- 매일 Windows 작업 스케줄러 01:00 KST 실행
- 데이터: blog_visitors.json
"""

import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NAVER_ID   = os.environ.get("NAVER_ID")
NAVER_PW   = os.environ.get("NAVER_PW")
BLOG_ID    = os.environ.get("BLOG_ID", "nature_food")
DATA_FILE   = "blog_visitors.json"
MONTHLY_FILE = "blog_visitors_monthly.json"
START_DATE  = "2026-03-01"


# ── Playwright 로그인 + 수집 ───────────────────────────────────────

async def fetch_stat_playwright(start_date: str) -> dict:
    """Playwright로 ID/PW 로그인 후 통계 API 데이터 수집.
    쿠키 파일 불필요 - 매번 직접 로그인."""
    from playwright.async_api import async_playwright

    if not NAVER_ID or not NAVER_PW:
        raise Exception("NAVER_ID/NAVER_PW 환경변수 미설정 (.env 파일 확인)")

    result = {}

    async def on_response(resp):
        if "blog.stat.naver.com/api/blog/daily/cv" in resp.url:
            try:
                data = await resp.json()
                stat_list = data.get("result", {}).get("statDataList", [])
                if stat_list:
                    rows = stat_list[0].get("data", {}).get("rows", {})
                    for d, c in zip(rows.get("date", []), rows.get("cv", [])):
                        result[d] = c
            except Exception as e:
                print(f"API 파싱 오류: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--lang=ko-KR",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1920, "height": 1080},
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
            Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)
        page = await context.new_page()

        # 로그인
        print(f"네이버 로그인 시도 (ID: {NAVER_ID[:3]}***)")
        await page.goto("https://nid.naver.com/nidlogin.login", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        await page.fill("#id", NAVER_ID)
        await asyncio.sleep(0.5)
        await page.fill("#pw", NAVER_PW)
        await asyncio.sleep(0.5)

        # IP보안 OFF 전환 (켜져 있으면 로그인 후 추가 인증 발생)
        try:
            toggle = page.locator(".set_ip_check, #ip_secure_check, [class*='ip']").first
            if await toggle.is_visible(timeout=2000):
                await toggle.click()
                await asyncio.sleep(0.5)
                print("IP보안 OFF 전환 완료")
        except Exception:
            pass

        await page.click(".btn_login")
        await asyncio.sleep(4)

        if "nidlogin" in page.url:
            await browser.close()
            raise Exception("네이버 로그인 실패 (IP 추가인증 또는 ID/PW 오류)")

        print("로그인 성공")

        # 통계 페이지 접속 + API 응답 캡처
        page.on("response", on_response)
        await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today", timeout=30000)
        await asyncio.sleep(8)
        page.remove_listener("response", on_response)

        await browser.close()

    return result


# ── 데이터 저장 ────────────────────────────────────────────────────

def load_existing_data() -> dict:
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(existing: dict, new_data: dict) -> dict:
    merged = dict(sorted({**existing, **new_data}.items()))
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def load_monthly_data() -> dict:
    if Path(MONTHLY_FILE).exists():
        with open(MONTHLY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_monthly_data(existing: dict, new_data: dict) -> dict:
    merged = dict(sorted({**existing, **new_data}.items()))
    with open(MONTHLY_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


# ── 월별 자동 갱신 ────────────────────────────────────────────────

def update_monthly_from_daily(daily: dict):
    """일별 데이터에서 완료된 달의 월별 합계 자동 갱신 (이번 달 제외)."""
    from collections import defaultdict

    KST = timezone(timedelta(hours=9))
    current_month = datetime.now(KST).strftime("%Y-%m")

    monthly_sums: dict[str, int] = defaultdict(int)
    for date_str, views in daily.items():
        month = date_str[:7]
        if month < current_month:
            monthly_sums[month] += int(views or 0)

    if not monthly_sums:
        return

    existing_monthly = load_monthly_data()
    updated_count = 0
    for month_str, total in monthly_sums.items():
        key = f"{month_str}-01"
        if existing_monthly.get(key) != total:
            existing_monthly[key] = total
            updated_count += 1

    if updated_count > 0:
        save_monthly_data({}, existing_monthly)
        print(f"월별 데이터 자동 갱신 완료: {updated_count}개월 업데이트")
    else:
        print("월별 데이터 변경 없음 (이미 최신)")


# ── 메인 ──────────────────────────────────────────────────────────

def main():
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    yesterday = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n[{now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST] 네이버 블로그 조회수 수집 시작")
    print(f"수집 기간: {START_DATE} ~ {yesterday}")
    print("방식: Playwright ID/PW 직접 로그인 (쿠키 불필요)")

    new_data = asyncio.run(fetch_stat_playwright(yesterday))

    if not new_data:
        raise Exception("블로그 조회수 수집 실패 - 로그인 후 API 응답 없음")

    new_data = {k: v for k, v in new_data.items() if k <= yesterday}
    existing = load_existing_data()
    merged = save_data(existing, new_data)
    print(f"일별 저장 완료: {DATA_FILE} ({len(merged)}일치)")

    update_monthly_from_daily(merged)


if __name__ == "__main__":
    main()
