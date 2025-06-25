@echo off
cd /d "C:\Шлях\до\твого\проєкту"
start cmd /k "streamlit run app.py"
timeout /t 5
start http://localhost:8501