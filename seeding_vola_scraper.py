#!/usr/bin/env python3
"""
Cle Seeding Vola 시트 수집기
- 협찬_업무시트(클레_Vola) 데이터를 seeding_vola_data.json으로 저장
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

SPREADSHEET_ID = "1fyqDmq8lZG9GyaoSco7rFGCTxXnITTCVb-KQ-XBFKww"
SHEET_NAME = "협찬_업무시트(클레_Vola)"
DATA_FILE = "seeding_vola_data.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def get_credentials():
    """서비스 계정 또는 환경변수(GitHub Secrets)에서 인증"""
    creds_env = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_env:
        info = json.loads(creds_env)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    if Path("google_credentials.json").exists():
        return Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)
    raise Exception("GOOGLE_CREDENTIALS 환경변수 또는 google_credentials.json 파일이 필요합니다.")


def fetch_sheet_data() -> list[dict]:
    creds = get_credentials()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)
    records = ws.get_all_records()
    print(f"수집 완료: {len(records)}행")
    return records


def main():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 시딩 Vola 시트 수집 시작")

    records = fetch_sheet_data()

    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows": records,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {DATA_FILE} ({len(records)}행)")


if __name__ == "__main__":
    main()
