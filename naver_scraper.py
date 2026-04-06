#!/usr/bin/env python3
"""
네이버 블로그 일별 조회수 수집기
- requests 직접 호출 방식 (Playwright fallback)
- 매일 GitHub Actions UTC 15:10 (KST 00:10) 실행
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
COOKIE_FILE = "naver_cookies.json"
DATA_FILE   = "blog_visitors.json"
MONTHLY_FILE = "blog_visitors_monthly.json"
START_DATE  = "2026-03-01"


# ── 쿠키 로드 ──────────────────────────────────────────────────────

def load_cookie_list_from_browser() -> list:
    """로컬 Chrome/Edge 브라우저에서 네이버 쿠키 직접 추출"""
    try:
        import browser_cookie3
        for loader, name in [(browser_cookie3.chrome, "Chrome"), (browser_cookie3.edge, "Edge")]:
            try:
                jar = loader(domain_name=".naver.com")
                cookies = [
                    {"name": c.name, "value": c.value,
                     "domain": c.domain or ".naver.com", "path": c.path or "/"}
                    for c in jar if c.value
                ]
                if cookies:
                    print(f"브라우저({name})에서 쿠키 로드: {len(cookies)}개")
                    return cookies
            except Exception:
                continue
    except ImportError:
        pass
    return []


def load_cookie_list() -> list:
    """브라우저 직접 추출 → 환경변수 → st.secrets → 파일 순서로 쿠키 로드"""
    # 1순위: 로컬 Chrome/Edge 쿠키 직접 추출 (크롤링 PC 전용, 항상 최신)
    browser_cookies = load_cookie_list_from_browser()
    if browser_cookies:
        return browser_cookies

    # 2순위: 환경변수 또는 파일
    cookie_env = os.environ.get("NAVER_COOKIES")
    if not cookie_env:
        try:
            import streamlit as st
            val = st.secrets["NAVER_COOKIES"]
            cookie_env = str(val)
        except Exception:
            pass
    if cookie_env:
        cookies = json.loads(cookie_env)
        print(f"쿠키 로드: {len(cookies)}개")
        return cookies
    if Path(COOKIE_FILE).exists():
        with open(COOKIE_FILE) as f:
            cookies = json.load(f)
        print(f"파일에서 쿠키 로드: {len(cookies)}개")
        return cookies
    return []


# ── 쿠키 저장 & GitHub Secret 자동 갱신 ──────────────────────────

def save_cookies_and_update_secret(cookie_list: list):
    """수집 성공 후 쿠키 파일 갱신 + GitHub Secret 자동 업데이트"""
    if not cookie_list:
        return
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookie_list, f, ensure_ascii=False, indent=2)
        print(f"쿠키 파일 갱신 완료: {len(cookie_list)}개")
    except Exception as e:
        print(f"쿠키 파일 저장 오류: {e}")

    # gh CLI로 GitHub Secret 자동 업데이트
    try:
        import subprocess
        pat = os.environ.get("GITHUB_PAT", "")
        env = os.environ.copy()
        if pat:
            env["GH_TOKEN"] = pat
        result = subprocess.run(
            ["gh", "secret", "set", "NAVER_COOKIES",
             "--body", json.dumps(cookie_list, ensure_ascii=False),
             "--repo", "Hwnagseunghwan/foodcarevblog-dashboard"],
            capture_output=True, text=True, timeout=30, env=env
        )
        if result.returncode == 0:
            print("GitHub Secret(NAVER_COOKIES) 자동 업데이트 완료")
        else:
            print(f"GitHub Secret 업데이트 실패: {result.stderr.strip()}")
    except Exception as e:
        print(f"GitHub Secret 업데이트 오류: {e}")


# ── requests 방식 (Playwright 불필요) ──────────────────────────────

def fetch_stat_api_requests(start_date: str) -> tuple[dict, list]:
    """requests.Session으로 네이버 통계 API 직접 호출.
    반환: (data_dict, updated_cookie_list)"""
    import requests

    cookie_list = load_cookie_list()
    if not cookie_list:
        raise Exception("쿠키 없음 - NAVER_COOKIES 환경변수 또는 naver_cookies.json 필요")

    session = requests.Session()
    for c in cookie_list:
        session.cookies.set(c["name"], c["value"],
                            domain=c.get("domain", ".naver.com"),
                            path=c.get("path", "/"))

    timestamp = int(datetime.now().timestamp() * 1000)
    url = (
        f"https://blog.stat.naver.com/api/blog/daily/cv"
        f"?timeDimension=DATE&startDate={start_date}&exclude=&_={timestamp}"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://admin.blog.naver.com/{BLOG_ID}/stat/today",
        "Accept": "application/json, text/plain, */*",
    }

    resp = session.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    stat_list = data.get("result", {}).get("statDataList", [])
    if not stat_list:
        raise Exception("API 응답 데이터 없음 (쿠키 만료 가능성)")

    rows = stat_list[0].get("data", {}).get("rows", {})
    result = dict(zip(rows.get("date", []), rows.get("cv", [])))

    # 응답 후 갱신된 쿠키 추출 (Session이 Set-Cookie 자동 반영)
    updated_cookies = [
        {"name": c.name, "value": c.value,
         "domain": c.domain or ".naver.com", "path": c.path or "/"}
        for c in session.cookies
    ]

    return result, updated_cookies


# ── Playwright 방식 (fallback) ────────────────────────────────────

async def _load_cookies_playwright(context):
    cookie_list = load_cookie_list()
    if cookie_list:
        await context.add_cookies(cookie_list)
        return True
    return False


async def _is_logged_in(page):
    await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(2)
    return "nidlogin" not in page.url


async def _login_playwright(page, context):
    if not NAVER_ID or not NAVER_PW:
        raise Exception("NAVER_ID/NAVER_PW 미설정")
    await page.goto("https://nid.naver.com/nidlogin.login", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)
    await page.fill("#id", NAVER_ID)
    await asyncio.sleep(0.5)
    await page.fill("#pw", NAVER_PW)
    await asyncio.sleep(0.5)
    # IP보안 ON → OFF 전환
    try:
        ip_toggle = page.locator(".set_ip_check").first
        if await ip_toggle.is_visible(timeout=2000):
            await ip_toggle.click()
            await asyncio.sleep(0.5)
            print("IP보안 OFF 전환 완료")
    except Exception:
        pass
    await page.click(".btn_login")
    await asyncio.sleep(3)
    if "nidlogin" in page.url:
        raise Exception("네이버 로그인 실패")
    print("로그인 성공")


async def _fetch_stat_playwright(start_date: str) -> tuple[dict, list]:
    from playwright.async_api import async_playwright
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
                "--disable-infobars",
                "--lang=ko-KR",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1920, "height": 1080},
        )
        # headless 탐지 우회 (navigator.webdriver 제거 등)
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
            Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)
        page = await context.new_page()
        cookie_loaded = await _load_cookies_playwright(context)
        if not cookie_loaded or not await _is_logged_in(page):
            await _login_playwright(page, context)

        page.on("response", on_response)
        await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today", timeout=30000)
        await asyncio.sleep(7)
        page.remove_listener("response", on_response)

        # 로그인 후 쿠키 추출 (다음 실행에서 재사용)
        raw_cookies = await context.cookies()
        cookie_list = [
            {"name": c["name"], "value": c["value"],
             "domain": c.get("domain", ".naver.com"), "path": c.get("path", "/")}
            for c in raw_cookies
        ]
        await browser.close()

    return result, cookie_list


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
    """일별 데이터에서 완료된 달의 월별 합계를 계산해 blog_visitors_monthly.json 자동 갱신.
    - 현재 진행 중인 달(이번 달)은 제외 (월이 끝나야 확정)
    - 기존 월별 데이터 유지, 일별 데이터가 있는 달만 덮어쓰기
    """
    from collections import defaultdict

    KST = timezone(timedelta(hours=9))
    current_month = datetime.now(KST).strftime("%Y-%m")

    # 일별 → 월별 합산 (완료된 달만)
    monthly_sums: dict[str, int] = defaultdict(int)
    for date_str, views in daily.items():
        month = date_str[:7]        # "2026-03"
        if month < current_month:  # 이번 달 제외
            monthly_sums[month] += int(views or 0)

    if not monthly_sums:
        return

    # 기존 monthly JSON 로드 후 덮어쓰기
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

    new_data = {}
    updated_cookies = []

    # 1차: requests 방식 (Session으로 응답 쿠키 자동 갱신)
    try:
        print("requests 방식으로 수집 시도...")
        new_data, updated_cookies = fetch_stat_api_requests(yesterday)
        print(f"requests 수집 성공: {len(new_data)}일치")
    except Exception as e:
        print(f"requests 실패: {e}")
        # 2차: Playwright fallback (stealth 모드 - headless 탐지 우회 + ID/PW 자동 로그인)
        try:
            print("Playwright 방식으로 재시도...")
            new_data, playwright_cookies = asyncio.run(_fetch_stat_playwright(yesterday))
            print(f"Playwright 수집 성공: {len(new_data)}일치")
            # Playwright 로그인으로 얻은 쿠키를 Secret에 저장 (자가복구)
            if not updated_cookies and playwright_cookies:
                updated_cookies = playwright_cookies
        except Exception as e2:
            print(f"Playwright 실패: {e2}")

    if not new_data:
        print("데이터 수집 실패")
        raise Exception("블로그 조회수 수집 실패 - 쿠키 만료 또는 인증 오류")

    new_data = {k: v for k, v in new_data.items() if k <= yesterday}
    existing = load_existing_data()
    merged = save_data(existing, new_data)
    print(f"일별 저장 완료: {DATA_FILE} ({len(merged)}일치)")

    # 일별 데이터로 월별 합계 자동 갱신 (완료된 달만)
    update_monthly_from_daily(merged)

    # 성공 시 쿠키 자동 갱신 & GitHub Secret 업데이트
    if updated_cookies:
        save_cookies_and_update_secret(updated_cookies)


if __name__ == "__main__":
    main()
