@echo off
REM Windows entrypoint - forwards to make.ps1 (paymentgate-style). Usage: make up_infra
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make.ps1" %*
