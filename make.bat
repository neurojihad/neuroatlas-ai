@echo off
REM Windows entrypoint - forwards to make.ps1. Same as make.cmd; .bat helps some PATH lookups.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make.ps1" %*
