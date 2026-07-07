@echo off
REM NeuroAtlas make shim for .venv\Scripts (on PATH when venv is active).
set "REPO_ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\make.ps1" %*
