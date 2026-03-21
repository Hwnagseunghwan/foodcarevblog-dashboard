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

def load_cookie_list() -> list:
    """환경변수 → st.secrets → 파일 순서로 쿠키 로드"""
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


# ── requests 방식 (Playwright 불필요) ──────────────────────────────

def fetch_stat_api_requests(start_date: str) -> dict:
    """requests로 네이버 통계 API 직접 호출"""
    import requests

    cookie_list = load_cookie_list()
    if not cookie_list:
        raise Exception("쿠키 없음 - NAVER_COOKIES 환경변수 또는 naver_cookies.json 필요")

    cookies = {c["name"]: c["value"] for c in cookie_list}
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

    resp = requests.get(url, cookies=cookies, headers=headers, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    stat_list = data.get("result", {}).get("statDataList", [])
    if not stat_list:
        raise Exception("API 응답 데이터 없음 (쿠키 만료 가능성)")

    rows = stat_list[0].get("data", {}).get("rows", {})
    return dict(zip(rows.get("date", []), rows.get("cv", [])))


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
    await page.click("#id")
    await page.type("#id", NAVER_ID, delay=80)
    await page.click("#pw")
    await page.type("#pw", NAVER_PW, delay=80)
    await page.click(".btn_login")
    await asyncio.sleep(3)
    if "nidlogin" in page.url:
        raise Exception("네이버 로그인 실패")
    print("로그인 성공")


async def _fetch_stat_playwright(start_date: str) -> dict:
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
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        cookie_loaded = await _load_cookies_playwright(context)
        if not cookie_loaded or not await _is_logged_in(page):
            await _login_playwright(page, context)

        page.on("response", on_response)
        await page.goto(f"https://admin.blog.naver.com/{BLOG_ID}/stat/today", timeout=30000)
        await asyncio.sleep(7)
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


# ── 메인 ──────────────────────────────────────────────────────────

def main():
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    yesterday = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n[{now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST] 네이버 블로그 조회수 수집 시작")
    print(f"수집 기간: {START_DATE} ~ {yesterday}")

    new_data = {}

    # 1차: requests 방식
    try:
        print("requests 방식으로 수집 시도...")
        new_data = fetch_stat_api_requests(START_DATE)
        print(f"requests 수집 성공: {len(new_data)}일치")
    except Exception as e:
        print(f"requests 실패: {e}")
        # 2차: Playwright fallback
        try:
            print("Playwright 방식으로 재시도...")
            new_data = asyncio.run(_fetch_stat_playwright(START_DATE))
            print(f"Playwright 수집 성공: {len(new_data)}일치")
        except Exception as e2:
            print(f"Playwright 실패: {e2}")

    if not new_data:
        print("데이터 수집 실패")
        raise Exception("블로그 조회수 수집 실패 - 쿠키 만료 또는 인증 오류")

    new_data = {k: v for k, v in new_data.items() if k <= yesterday}
    existing = load_existing_data()
    merged = save_data(existing, new_data)
    print(f"일별 저장 완료: {DATA_FILE} ({len(merged)}일치)")


if __name__ == "__main__":
    main()
