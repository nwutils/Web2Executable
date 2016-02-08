
rm -rf Web2ExeLinux*.zip
rm -rf Web2ExeLinux-CMD

VERSION=$(cat files/version.txt)

pyinstaller --onefile --hidden-import PIL.Jpeg2KImagePlugin --hidden-import pkg_resources --hidden-import PIL._imaging --hidden-import configobj --distpath Web2ExeLinux-CMD -n web2exe-linux command_line.py
cp -rf files Web2ExeLinux-CMD/files
rm -rf Web2ExeLinux-CMD/files/downloads/*
rm Web2ExeLinux-CMD/files/error.log Web2ExeLinux-CMD/files/last_project_path.txt Web2ExeLinux-CMD/files/recent_files.txt Web2ExeLinux-CMD/files/compressors/upx-mac Web2ExeLinux-CMD/files/compressors/upx-win.exe

rm -rf Web2ExeLinux
pyinstaller -F --hidden-import PIL.Jpeg2KImagePlugin --hidden-import configobj --hidden-import PIL._imaging --hidden-import pkg_resources -n web2exe --distpath Web2ExeLinux main.py
cp -rf files Web2ExeLinux/files
rm -rf Web2ExeLinux/files/downloads/*
rm Web2ExeLinux/files/error.log Web2ExeLinux/files/last_project_path.txt Web2ExeLinux/files/recent_files.txt Web2ExeLinux/files/compressors/upx-mac Web2ExeLinux/files/compressors/upx-win.exe


zip -r -9 Web2ExeLinux-CMD.zip Web2ExeLinux-CMD/*
zip -r -9 Web2ExeLinux-${VERSION}.zip Web2ExeLinux

python3.4 upload_release.py
