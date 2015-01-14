rm -rf command_line_builds/files
pyinstaller --hidden-import configobj --distpath command_line_builds --onefile -n web2exe-mac command_line.py
cp -rf files command_line_builds/files/

rm -rf build dist Web2Executable.app

sudo python build_mac_setup.py py2app --iconfile icon.icns 

sudo chown -R joey dist/main.app
sudo chown -R joey dist/ build/
mv dist/main.app Web2Executable.app

rm -rf build dist
