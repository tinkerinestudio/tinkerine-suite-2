setlocal EnableDelayedExpansion
for /f "delims=" %%x in (python_files_to_localize) do set var=!var! ..\..\%%x
echo !var!
..\..\..\python\python.exe pygettext.py -d tinkerine -o tinkerine.pot !var!
endlocal