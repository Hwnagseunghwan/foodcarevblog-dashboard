@echo off
cd /d C:\foodcarevblog-dashboard
git pull
C:\Users\USER\miniconda3\Scripts\streamlit.exe run dashboard.py
pause
