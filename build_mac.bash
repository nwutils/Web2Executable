VERSION=$(cat files/version.txt)

rm -rf Web2ExeMac*
rm  files/error.log files/last_project_path.txt files/recent_files.txt
rm -rf files/downloads/*
rm -rf Web2ExeMac-CMD/files
pyinstaller --hidden-import PIL.Jpeg2KImagePlugin --hidden-import configobj --hidden-import pkg_resources --distpath Web2ExeMac-CMD --onefile -n web2exe-mac command_line.py
cp -rf files Web2ExeMac-CMD/files/

rm -rf build dist Web2Executable.app

#sudo python build_mac_setup.py py2app --iconfile icon.icns 
pyinstaller -w --hidden-import PIL.Jpeg2KImagePlugin --hidden-import PyQt4 --hidden-import PIL --hidden-import configobj --hidden-import pkg_resources --distpath Web2ExeMac --onefile -n Web2Executable main.py

#sudo chown -R joey dist/Web2Executable.app
#sudo chown -R joey dist/ build/
#mv dist/Web2Executable.app Web2Executable.app

mv Web2ExeMac/Web2Executable.app .

#rm -rf Web2Executable.app/Contents/Frameworks/QtDesigner*
#rm -rf Web2Executable.app/Contents/Frameworks/QtXml*
#rm -rf Web2Executable.app/Contents/Frameworks/QtWebKit*
#rm -rf Web2Executable.app/Contents/Frameworks/QtScript*

cp icon.icns Web2Executable.app/Contents/Resources/icon-windowed.icns
cp -rf files Web2Executable.app/Contents/MacOS/

rm -rf build dist

/Applications/Keka.app/Contents/Resources/keka7z a -r Web2ExeMac-CMD.zip Web2ExeMac-CMD
/Applications/Keka.app/Contents/Resources/keka7z a -r Web2ExeMac-${VERSION}.zip Web2Executable.app

python3.4 upload_release.py
