@echo off
setlocal
set ROOT=%~dp0..
pushd "%ROOT%"
py -3 -m collector collect-once %*
set EC=%ERRORLEVEL%
if %EC% EQU 9009 (
    python -m collector collect-once %*
    set EC=%ERRORLEVEL%
)
popd
exit /b %EC%
