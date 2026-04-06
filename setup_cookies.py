"""
크롤링 PC 최초 쿠키 설정 스크립트 (한 번만 실행)
실행: python setup_cookies.py
브라우저 창이 열리면 네이버 로그인 후 창을 닫지 마세요.
로그인 완료 후 자동으로 쿠키가 저장됩니다.
"""
import asyncio
import json
from playwright.async_api import async_playwright

COOKIE_FILE = "naver_cookies.json"

async def main():
    print("=" * 50)
    print("네이버 쿠키 설정 스크립트")
    print("=" * 50)
    print("브라우저 창이 열립니다. 네이버에 로그인해주세요.")
    print("로그인 완료 후 자동으로 쿠키가 저장됩니다.")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto("https://nid.naver.com/nidlogin.login")

        print("로그인 감지 대기 중... (최대 120초)")
        for i in range(120):
            await asyncio.sleep(1)
            if "nidlogin" not in page.url:
                print(f"로그인 감지됨! (URL: {page.url[:50]})")
                break
        else:
            print("시간 초과 - 로그인이 감지되지 않았습니다.")
            await browser.close()
            return

        await asyncio.sleep(2)

        # 쿠키 수집
        cookies = await context.cookies()
        naver_cookies = [
            {"name": c["name"], "value": c["value"],
             "domain": c.get("domain", ".naver.com"), "path": c.get("path", "/")}
            for c in cookies if "naver.com" in c.get("domain", "")
        ]

        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(naver_cookies, f, ensure_ascii=False, indent=2)

        print(f"쿠키 저장 완료: {COOKIE_FILE} ({len(naver_cookies)}개)")
        print()
        print("이제 naver_scraper.py가 자동으로 동작합니다.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
