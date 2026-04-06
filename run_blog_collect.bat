@echo off
chcp 65001 > nul
cd /d C:\foodcarevblog-dashboard

set LOG=C:\foodcarevblog-dashboard\scraper.log

echo [%date% %time%] 블로그 조회수 수집 시작 >> %LOG% 2>&1

:: 파이썬 실행 (miniconda 환경)
call C:\Users\USER\miniconda3\Scripts\activate.bat >> %LOG% 2>&1
if errorlevel 1 (
    call C:\Users\USER\Anaconda3\Scripts\activate.bat >> %LOG% 2>&1
)

python naver_scraper.py >> %LOG% 2>&1
set RESULT=%ERRORLEVEL%

if %RESULT% EQU 0 (
    echo [%date% %time%] 수집 성공 - GitHub 업로드 중... >> %LOG% 2>&1
    git add blog_visitors.json blog_visitors_monthly.json naver_cookies.json >> %LOG% 2>&1
    git diff --staged --quiet
    if errorlevel 1 (
        git commit -m "data: %date% 블로그 조회수 업데이트 (로컬 자동수집)" >> %LOG% 2>&1
        git push >> %LOG% 2>&1
        echo [%date% %time%] GitHub 업로드 완료 >> %LOG% 2>&1
    ) else (
        echo [%date% %time%] 변경 데이터 없음 (이미 최신) >> %LOG% 2>&1
    )
) else (
    echo [%date% %time%] 수집 실패 >> %LOG% 2>&1
)

:: 로그 최근 500줄만 유지
powershell -Command "if ((Get-Item '%LOG%').length -gt 500KB) { Get-Content '%LOG%' -Tail 500 | Set-Content '%LOG%_tmp'; Move-Item '%LOG%_tmp' '%LOG%' -Force }" >> nul 2>&1
