rm -rf command_line_builds

pyinstaller --onefile --hidden-import configobj --distpath command_line_builds -n web2exe-linux command_line.py
cp -rf files command_line_builds/files
rm -rf command_line_builds/files/downloads/*

rm -rf Web2ExeLinux
pyinstaller -F --hidden-import configobj -n web2exe --distpath Web2ExeLinux main.py
cp -rf files Web2ExeLinux/files
rm -rf Web2ExeLinux/files/downloads/*
