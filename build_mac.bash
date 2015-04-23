rm -rf Web2ExeMac*
rm  files/error.log files/last_project_path.txt files/recent_files.txt
rm -rf files/downloads/*
rm -rf Web2ExeMac-CMD/files
pyinstaller --hidden-import Jpeg2KImagePlugin --hidden-import configobj --distpath Web2ExeMac-CMD --onefile -n web2exe-mac command_line.py
cp -rf files Web2ExeMac-CMD/files/

rm -rf build dist Web2Executable.app

sudo python build_mac_setup.py py2app --iconfile icon.icns 

sudo chown -R joey dist/main.app
sudo chown -R joey dist/ build/
mv dist/main.app Web2Executable.app

rm -rf Web2Executable.app/Contents/Frameworks/Qt*

rm -rf build dist

zip -r -9 Web2ExeMac-CMD.zip Web2ExeMac-CMD
zip -r -9 Web2ExeMac-v0.2.2b.zip Web2Executable.app
