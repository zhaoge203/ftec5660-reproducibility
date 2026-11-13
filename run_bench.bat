@echo off
cd /d F:\cuhk\5510A\5660\ftec5660-repro
for /f "usebackq tokens=1,2 delims==" %%A in (".env") do set %%A=%%B
set HF_ENDPOINT=https://hf-mirror.com
set PYTHONPATH=F:\cuhk\5510A\5660\memory-benchmarks
set CUTOFFS=%3
set CUTOFFS=%CUTOFFS:_=,%
".venv\Scripts\python.exe" -m benchmarks.locomo.run --project-name %1 --dataset-path datasets\locomo\locomo10.json --conversations %2 --top-k-cutoffs %CUTOFFS% --answerer-model deepseek-chat --judge-model deepseek-chat --provider openai --max-workers 8 --rpm 120 %4 %5 > logs\bench_%1.log 2>&1
