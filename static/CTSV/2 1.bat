@echo off

:start
set first=0
echo ::::::::::::
echo ***************************************************************
echo (.) [EXIT]
echo (1) [Backup] CTS-Verifier
echo (2) [Restore]CTS-Verifier
echo ***************************************************************
set /p first="Input your selection: "
if %first% EQU 1 (
adb wait-for-device
echo "[Backup] CTS-Verifier"
rem del /F /Q databases
rd /S /Q databases
md databases
adb exec-out "run-as com.android.cts.verifier cat databases/results.db" > databases/results.db
goto start
)
if %first% EQU 2 (
adb wait-for-device
echo "[Restore]CTS-Verifier"
adb shell am force-stop com.android.cts.verifier
adb shell rm -rf /data/local/tmp/databases
adb push databases /data/local/tmp/
adb shell run-as com.android.cts.verifier cp -r /data/local/tmp/databases/results.db databases/results.db
adb shell am start -n com.android.cts.verifier/.CtsVerifierActivity
del /F /Q databases
goto start
)
if %first% EQU . (
exit
)
cls
echo Input error => [%first%]... Please try again,
goto start