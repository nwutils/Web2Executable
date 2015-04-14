rm -rf Web2ExeLinux-CMD

pyinstaller --onefile --hidden-import configobj --distpath Web2ExeLinux-CMD -n web2exe-linux command_line.py
cp -rf files Web2ExeLinux-CMD/files
rm -rf Web2ExeLinux-CMD/files/downloads/*

rm -rf Web2ExeLinux
pyinstaller -F --hidden-import configobj -n web2exe --distpath Web2ExeLinux main.py
cp -rf files Web2ExeLinux/files
rm -rf Web2ExeLinux/files/downloads/*

zip -r -9 Web2ExeLinux-CMD.zip Web2ExeLinux-CMD/*
zip -r -9 Web2ExeLinux-v0.2.0.zip Web2ExeLinux
