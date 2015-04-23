rd /S /Q Web2ExeWin
call pyinstaller --onefile --hidden-import PIL.Jpeg2KImagePlugin --hidden-import configobj -i icon.ico --distpath command_line_builds -n web2exe-win command_line.py
rd /S /Q command_line_builds\files
echo D | xcopy /s files command_line_builds\files


call pyinstaller -w --onefile --hidden-import PIL.Jpeg2KImagePlugin --hidden-import configobj -i icon.ico --distpath Web2ExeWin -n Web2Exe main.py
echo D | xcopy /s files Web2ExeWin\files
