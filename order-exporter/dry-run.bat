@echo off
rem Test run with the sample file: no browser, no login. Output goes to output\dry-run.
cd /d "%~dp0"
call run.bat --dry-run %*
