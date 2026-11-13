@echo off
cd /d F:\cuhk\5510A\5660\ftec5660-repro
set HF_ENDPOINT=https://hf-mirror.com
if "%QDRANT_PATH%"=="" set QDRANT_PATH=F:\cuhk\5510A\5660\ftec5660-repro\qdrant
".venv\Scripts\python.exe" -m uvicorn server.shim_server:app --host 127.0.0.1 --port 8888 >> shim.log 2>&1
