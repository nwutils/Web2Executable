rm -rf command_line_builds/files
pyinstaller --onefile --hidden-import configobj --distpath command_line_builds -n web2exe-linux command_line.py
cp -rf files command_line_builds/files
