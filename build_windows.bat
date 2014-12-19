rd /S /Q Web2ExeWin
call pyinstaller --onefile --hidden-import configobj --distpath command_line_builds -n web2exe command_line.py
echo D | xcopy /s files output\files

call cxfreeze.bat main.py --target-dir=Web2ExeWin --base-name=Win32GUI
echo D | xcopy /s files Web2ExeWin\files
