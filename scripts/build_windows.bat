rd /S /Q Web2ExeWin
rd /S /Q build
del *.zip
call pyinstaller --onefile ^
 --hidden-import PIL.Jpeg2KImagePlugin ^
 --hidden-import configobj ^
 --hidden-import pkg_resources ^
 -i images\icon.ico ^
 --distpath Web2ExeWin-CMD ^
 -n web2exe-win command_line.py

rd /S /Q Web2ExeWin-CMD\files
echo D | xcopy /s files Web2ExeWin-CMD\files


call pyinstaller -w --onefile ^
 --hidden-import PIL.Jpeg2KImagePlugin ^
 --hidden-import pkg_resources ^
 --hidden-import configobj ^
 -i images\icon.ico ^
 --distpath Web2ExeWin -n Web2Exe main.py

echo D | xcopy /s files Web2ExeWin\files

del Web2ExeWin\files\compressors\upx-mac
del Web2ExeWin\files\compressors\upx-linux-x64
del Web2ExeWin\files\compressors\upx-linux-x32

del Web2ExeWin-CMD\files\compressors\upx-mac
del Web2ExeWin-CMD\files\compressors\upx-linux-x64
del Web2ExeWin-CMD\files\compressors\upx-linux-x32

makensis /V4 scripts/Web2Exe.nsi

set /p Version=<files\version.txt

7z a Web2ExeWin-%Version%.zip -r Web2ExeWin
cd Web2ExeWin-CMD
7z a ..\Web2ExeWin-CMD.zip -tzip -r *
cd ..
7z a Web2ExeWin-Setup.zip Web2Exe-Setup.exe

call python scripts/upload_release.py
