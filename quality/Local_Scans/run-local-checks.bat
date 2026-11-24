@echo off
setlocal
pushd "%~dp0..\.." || exit /b 2
where py >nul 2>nul
if errorlevel 1 (
    python -m quality.Local_Scans.run_local_checks %*
) else (
    py -3 -m quality.Local_Scans.run_local_checks %*
)
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
