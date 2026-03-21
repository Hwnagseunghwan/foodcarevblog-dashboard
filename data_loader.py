"""
GitHub raw URL에서 JSON 데이터를 직접 로드.
Streamlit Cloud 재배포 없이 항상 최신 데이터 반영.
"""
import requests

REPO_RAW = "https://raw.githubusercontent.com/Hwnagseunghwan/foodcarevblog-dashboard/master"

def load_json(filename: str) -> dict:
    resp = requests.get(f"{REPO_RAW}/{filename}", timeout=10)
    resp.raise_for_status()
    return resp.json()
