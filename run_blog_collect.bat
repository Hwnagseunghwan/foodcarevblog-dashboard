@echo off
chcp 65001 > nul
cd /d C:\foodcarevblog-dashboard

echo [%date% %time%] 블로그 조회수 수집 시작

:: 파이썬 실행 (miniconda 환경)
call C:\Users\USER\miniconda3\Scripts\activate.bat 2>nul
if errorlevel 1 (
    call C:\Users\USER\Anaconda3\Scripts\activate.bat 2>nul
)

python naver_scraper.py
set RESULT=%ERRORLEVEL%

if %RESULT% EQU 0 (
    echo [%date% %time%] 수집 성공 - GitHub 업로드 중...
    git add blog_visitors.json blog_visitors_monthly.json
    git diff --staged --quiet
    if errorlevel 1 (
        git commit -m "data: %date% 블로그 조회수 업데이트 (로컬 자동수집)"
        git push
        echo [%date% %time%] GitHub 업로드 완료
    ) else (
        echo [%date% %time%] 변경 데이터 없음 (이미 최신)
    )
) else (
    echo [%date% %time%] 수집 실패 - 쿠키 갱신 필요 (python get_cookies.py 실행)
)
