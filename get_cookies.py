import asyncio, json
from playwright.async_api import async_playwright

TIMEOUT_SEC = 120  # 로그인 대기 최대 시간 (초)

async def manual_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        await page.goto('https://nid.naver.com/nidlogin.login', wait_until='domcontentloaded')
        print(f'브라우저에서 네이버에 직접 로그인하세요. (최대 {TIMEOUT_SEC}초 대기)')

        # 로그인 완료 감지: 로그인 페이지를 벗어날 때까지 대기
        for i in range(TIMEOUT_SEC):
            await asyncio.sleep(1)
            if "nidlogin" not in page.url:
                print(f"로그인 감지! ({i+1}초 소요) 현재 URL: {page.url}")
                break
            if i % 10 == 9:
                print(f"  대기 중... ({i+1}초 경과)")
        else:
            print("타임아웃: 로그인이 완료되지 않았습니다.")
            await browser.close()
            return

        await asyncio.sleep(2)  # 쿠키 세팅 안정화
        cookies = await context.cookies()
        with open('nature_food_cookies.json', 'w') as f:
            json.dump(cookies, f)
        print(f'쿠키 저장 완료: {len(cookies)}개 → nature_food_cookies.json')
        await browser.close()

asyncio.run(manual_login())
