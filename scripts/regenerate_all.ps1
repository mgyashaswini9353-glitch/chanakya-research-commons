# Reproducibly regenerate synthetic dataset, embeddings, PageRank, DuckDB warehouse, and ML evaluations
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$PyExe = Join-Path $Root ".venv\Scripts\python.exe"

& $PyExe "scripts\bootstrap_all.py"
& $PyExe "scripts\generate_diagrams.py"
& $PyExe "evaluation\run_evaluations.py"
& $PyExe -m pytest -v "tests\test_platform.py"
