rm -rf Web2ExeMac-CMD/files
pyinstaller --hidden-import configobj --distpath Web2ExeMac-CMD --onefile -n web2exe-mac command_line.py
cp -rf files Web2ExeMac-CMD/files/

rm -rf build dist Web2Executable.app

sudo python build_mac_setup.py py2app --iconfile icon.icns 

sudo chown -R joey dist/main.app
sudo chown -R joey dist/ build/
mv dist/main.app Web2Executable.app

rm -rf build dist

zip -r -9 Web2ExeMac-CMD.zip Web2ExeMac-CMD
zip -r -9 Web2ExeMac-v0.2.0b.zip Web2Executable.app
