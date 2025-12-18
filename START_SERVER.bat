@echo off
echo Starting Django Backend Server...
echo.
cd /d "%~dp0"
python manage.py runserver
pause


