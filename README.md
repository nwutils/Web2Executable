Web2Executable
==============

Uses node-webkit to generate "native" apps for already existing web apps.

Requires the pyside library and python 2.X to run. I've only tested the code on python 2.7.3-2.7.5, so I can't speak about any lower version, but it should work as long as PySide is supported.

Note: I have tested this with an already existing node application (leximail) and it currently will overwrite any existing package.json. I'm going to fix it to only touch the json fields that it needs to instead of overwriting the whole file. Until then, make backups of your package.json!

Getting Started
---------------

Run with:

```
python main.py
```

It's a pretty simple app. Just point it the the directory that your web application lives, customize the options (the two marked with a star are the only ones required) and then choose your export options. The app will export under YOUR_OUTPUT_DIR/YOUR_APP_NAME. 

What's New In v0.1.0b?
----------------------

Not too much. Some stability fixes and proper disabling of UI during download and extraction.

Prebuilt Binaries
-----------------

###Mac OS X

[Mac OS X 10.7+ download - v0.1.0b](http://www.mediafire.com/download/gw9z0hr76e78y5y/Web2ExeMac-v0.1.0b.zip)

Older Versions:

[Mac OS X 10.7+ download - v0.0.9b](http://www.mediafire.com/download/9gc23kmdonqqp5p/Web2ExeMac.zip)

You can just put the app where ever you want and double click to run it.

###Windows

[Windows 7+ download - v0.1.1b](http://www.mediafire.com/download/8l31crlxm5cb61n/Web2ExeWin-v0.1.1b.zip)

(extra minor version to fix a temporary directory issue only with windows)

Older Versions:

[Windows 7+ download - v0.0.9b](http://www.mediafire.com/download/utbddnfn27rc5uq/Web2ExeWin.zip)

Double click the Win2Exe.exe file inside the extracted folder.

###Linux

Only on Ubuntu 12.04. If someone knows how to make them on all linux distros, let me know. I'm using cx_Freeze to compile them to standalone apps. You must copy all .so.X.X files to either /usr/local/lib/ or /usr/lib/ for it to work.

[Linux 64bit download - v0.1.0b](http://www.mediafire.com/download/csd3bhdnmpam73v/Web2ExeLinux64-v0.1.0b.zip)

[Linux 32bit download - v0.1.0b](http://www.mediafire.com/download/g20gqguh2qw8dp8/Web2ExeLinux32-v0.1.0b.zip)

Older versions:

[Linux 64bit download - v0.0.9b](http://www.mediafire.com/download/purz88rpayt99ri/Web2ExeLinux64.zip) 

[Linux 32bit download - v0.0.9b](http://www.mediafire.com/download/pfiabmhbxdge9a3/Web2ExeLinux32.zip)

chmod 755 the Web2Exe binary inside the extracted folder and then run by double clicking or ./Web2Exe from the command line. Also, if you get shared library errors, you need to copy all the .so files into /usr/lib/ or /usr/local/lib/. Make sure you check to see if any libraries in /usr/lib/ conflict with the files first.

```
chmod 755 Web2Exe
sudo cp *.so.* /usr/lib/
```

Note: For some reason, these linux binaries are not working correctly on vanilla systems. I'm looking into the issue and will update them when I figure out what is going on.


Features
--------

Supports exporting web applications to Mac, Linux, and Windows. So far, it works with all the apps I've tested it with. It supports Phaser and I assume it supports all other html5 and javascript libraries because it uses the same engine Google Chrome uses.

Future Features
---------------

- Automatic replacement of icon files inside of Mac apps and Windows exes. Right now, the only way to have a custom Mac icon is to convert your image to .icns format and put it in the resources folder of the app. For windows, you have to use a utility like Resource Hacker.

Screenshots
-----------

![Screenshot](http://i.imgur.com/V1609ea.png) 


