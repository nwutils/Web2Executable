Web2Executable
==============

Uses node-webkit to generate "native" apps for already existing web apps.

Requires the pyside library to run. 

Getting Started
---------------

Run with:

```
python main.py
```

It's a pretty simple app. Just point it the the directory that your web application lives, customize the options (the two marked with a star are the only ones required) and then choose your export options. The app will export under YOUR_OUTPUT_DIR/YOUR_APP_NAME. 

Prebuilt Binaries
-----------------

###Mac OS X

[Mac OS X 10.7+ download](http://www.mediafire.com/download/9gc23kmdonqqp5p/Web2ExeMac.zip)

You can just put the app where ever you want and double click to run it.

###Windows

[Windows 7+ download](http://www.mediafire.com/download/utbddnfn27rc5uq/Web2ExeWin.zip)

Double click the Win2Exe.exe file inside the extracted folder.

###Linux

[Linux 64bit download](http://www.mediafire.com/download/purz88rpayt99ri/Web2ExeLinux64.zip) (Broken Right Now)

[Linux 32bit download](http://www.mediafire.com/download/pfiabmhbxdge9a3/Web2ExeLinux32.zip) (Broken Right Now)

chmod 755 the Web2Exe binary inside the extracted folder and then run by double clicking or ./Web2Exe from the command line.

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


