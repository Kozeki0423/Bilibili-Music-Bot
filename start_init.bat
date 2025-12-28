@echo off
title Kozeki_UserInterface
cd /d "%~dp0"
if exist "ui.py" (
    start python ui.py
) else (
    echo Error: ui.py not found in current directory!
    pause
)