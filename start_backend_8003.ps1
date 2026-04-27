$ErrorActionPreference = "Stop"

Set-Location "D:\multi_debate_system"
$env:PYTHONUNBUFFERED = "1"

& ".\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8003
