rm -rf freeze

cxfreeze main.py --target-dir=freeze --include-modules=PySide.QtGui,PySide,PySide.QtNetwork,PySide.QtCore
chmod 755 freeze/*
cp -rf freeze/* Web2Executable.app/Contents/MacOS/

install_name_tool -change /usr/local/Cellar/pyside/1.2.1/lib/libpyside-python2.7.1.2.dylib @executable_path/libpyside-python2.7.1.2.dylib Web2Executable.app/Contents/MacOS/PySide.QtCore.so
install_name_tool -change /usr/local/lib/libshiboken-python2.7.1.2.1.dylib @executable_path/libshiboken-python2.7.1.2.1.dylib Web2Executable.app/Contents/MacOS/PySide.QtCore.so
install_name_tool -change /usr/local/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/PySide.QtCore.so

install_name_tool -change /usr/local/Cellar/pyside/1.2.1/lib/libpyside-python2.7.1.2.dylib @executable_path/libpyside-python2.7.1.2.dylib Web2Executable.app/Contents/MacOS/PySide.QtGui.so
install_name_tool -change /usr/local/lib/libshiboken-python2.7.1.2.1.dylib @executable_path/libshiboken-python2.7.1.2.1.dylib Web2Executable.app/Contents/MacOS/PySide.QtGui.so
install_name_tool -change /usr/local/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/PySide.QtGui.so
install_name_tool -change /usr/local/lib/QtGui.framework/Versions/4/QtGui @executable_path/QtGui Web2Executable.app/Contents/MacOS/PySide.QtGui.so

install_name_tool -change /usr/local/Cellar/pyside/1.2.1/lib/libpyside-python2.7.1.2.dylib @executable_path/libpyside-python2.7.1.2.dylib Web2Executable.app/Contents/MacOS/PySide.QtNetwork.so
install_name_tool -change /usr/local/lib/libshiboken-python2.7.1.2.1.dylib @executable_path/libshiboken-python2.7.1.2.1.dylib Web2Executable.app/Contents/MacOS/PySide.QtNetwork.so
install_name_tool -change /usr/local/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/PySide.QtNetwork.so
install_name_tool -change /usr/local/lib/QtNetwork.framework/Versions/4/QtNetwork @executable_path/QtNetwork Web2Executable.app/Contents/MacOS/PySide.QtNetwork.so

install_name_tool -change /usr/local/lib/libpyside-python2.7.1.2.1.dylib @executable_path/libpyside-python2.7.1.2.1.dylib Web2Executable.app/Contents/MacOS/libpyside-python2.7.1.2.dylib
install_name_tool -change /usr/local/lib/libshiboken-python2.7.1.2.1.dylib @executable_path/libshiboken-python2.7.1.2.1.dylib Web2Executable.app/Contents/MacOS/libpyside-python2.7.1.2.dylib
install_name_tool -change /usr/local/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/libpyside-python2.7.1.2.dylib

install_name_tool -change /usr/local/lib/libpyside-python2.7.1.2.1.dylib @executable_path/libpyside-python2.7.1.2.1.dylib Web2Executable.app/Contents/MacOS/libpyside-python2.7.1.2.1.dylib
install_name_tool -change /usr/local/lib/libshiboken-python2.7.1.2.1.dylib @executable_path/libshiboken-python2.7.1.2.1.dylib Web2Executable.app/Contents/MacOS/libpyside-python2.7.1.2.1.dylib
install_name_tool -change /usr/local/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/libpyside-python2.7.1.2.1.dylib


install_name_tool -change /usr/local/lib/QtGui.framework/Versions/4/QtGui @executable_path/QtGui Web2Executable.app/Contents/MacOS/QtGui
install_name_tool -change /usr/local/Cellar/qt/4.8.5/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/QtGui


install_name_tool -change /usr/local/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/QtCore


install_name_tool -change /usr/local/lib/QtNetwork.framework/Versions/4/QtNetwork @executable_path/QtNetwork Web2Executable.app/Contents/MacOS/QtNetwork
install_name_tool -change /usr/local/Cellar/qt/4.8.5/lib/QtCore.framework/Versions/4/QtCore @executable_path/QtCore Web2Executable.app/Contents/MacOS/QtNetwork
