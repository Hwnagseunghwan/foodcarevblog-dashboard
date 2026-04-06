"""
자동 로그인 + 데이터 수집 + GitHub push 테스트 스크립트
실행: python setup_cookies.py

1. .env의 NAVER_ID/NAVER_PW로 자동 로그인 (브라우저 창 표시)
2. 쿠키 저장
3. 블로그 조회수 데이터 수집
4. GitHub push → 대시보드 자동 업데이트
"""
import asyncio
import json
import os
import subprocess
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

NAVER_ID   = os.environ.get("NAVER_ID")
NAVER_PW   = os.environ.get("NAVER_PW")
COOKIE_FILE = "naver_cookies.json"


# ── 1단계: 자동 로그인 & 쿠키 저장 ───────────────────────────────

async def auto_login_and_save() -> bool:
    if not NAVER_ID or not NAVER_PW:
        print("❌ .env 파일에 NAVER_ID 또는 NAVER_PW가 없습니다.")
        print("   .env 파일 내용 확인: NAVER_ID=아이디, NAVER_PW=비밀번호")
        return False

    print(f"   네이버 ID: {NAVER_ID[:3]}*** / 브라우저 창이 열립니다...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 창 보이게 실행 (bot 탐지 우회)
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1280, "height": 800},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = await context.new_page()

        await page.goto("https://nid.naver.com/nidlogin.login", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # 아이디/비밀번호 입력
        await page.fill("#id", NAVER_ID)
        await asyncio.sleep(0.5)
        await page.fill("#pw", NAVER_PW)
        await asyncio.sleep(0.5)
        await page.click(".btn_login")
        print("   로그인 버튼 클릭 - 결과 대기 중... (최대 30초)")

        # 로그인 완료 감지
        for _ in range(30):
            await asyncio.sleep(1)
            if "nidlogin" not in page.url:
                print(f"   로그인 성공!")
                break
        else:
            print("   ❌ 로그인 실패")
            print("   → 캡차 또는 추가인증이 필요할 수 있습니다.")
            print("   → 브라우저 창에서 직접 완료해주세요. (30초 추가 대기)")
            for _ in range(30):
                await asyncio.sleep(1)
                if "nidlogin" not in page.url:
                    print("   수동 로그인 완료 감지!")
                    break
            else:
                await browser.close()
                return False

        await asyncio.sleep(2)

        # 쿠키 저장
        cookies = await context.cookies()
        naver_cookies = [
            {"name": c["name"], "value": c["value"],
             "domain": c.get("domain", ".naver.com"), "path": c.get("path", "/")}
            for c in cookies if "naver.com" in c.get("domain", "")
        ]
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(naver_cookies, f, ensure_ascii=False, indent=2)
        print(f"   쿠키 저장 완료: {len(naver_cookies)}개 → {COOKIE_FILE}")
        await browser.close()

    return True


# ── 2단계: 데이터 수집 ────────────────────────────────────────────

def collect_data() -> bool:
    result = subprocess.run(["python", "naver_scraper.py"])
    return result.returncode == 0


# ── 3단계: GitHub push ────────────────────────────────────────────

def push_to_github():
    subprocess.run(["git", "add", "blog_visitors.json", "blog_visitors_monthly.json", "naver_cookies.json"])
    diff = subprocess.run(["git", "diff", "--staged", "--quiet"])
    if diff.returncode != 0:
        today = datetime.now().strftime("%Y-%m-%d")
        subprocess.run(["git", "commit", "-m", f"data: {today} 블로그 조회수 업데이트 (로컬 자동수집)"])
        result = subprocess.run(["git", "push"])
        if result.returncode == 0:
            print("   GitHub push 완료 → 대시보드 업데이트 중...")
        else:
            print("   ❌ push 실패 - git 인증 확인 필요")
    else:
        print("   변경 데이터 없음 (이미 최신)")


# ── 메인 ─────────────────────────────────────────────────────────

async def main():
    print("=" * 50)
    print("[1/3] 네이버 자동 로그인")
    print("=" * 50)
    if not await auto_login_and_save():
        return

    print()
    print("=" * 50)
    print("[2/3] 블로그 조회수 데이터 수집")
    print("=" * 50)
    if not collect_data():
        print("❌ 데이터 수집 실패")
        return

    print()
    print("=" * 50)
    print("[3/3] GitHub push")
    print("=" * 50)
    push_to_github()

    print()
    print("✅ 모든 단계 완료!")
    print("   약 1~2분 후 대시보드에서 오늘 데이터를 확인하세요.")


if __name__ == "__main__":
    asyncio.run(main())
