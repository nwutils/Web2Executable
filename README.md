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

Features
--------

Supports exporting web applications to Mac, Linux, and Windows. So far, it works with all the apps I've tested it with. It supports Phaser and I assume it supports all other html5 and javascript libraries because it uses the same engine Google Chrome uses.

Future Features
---------------

- Automatic replacement of icon files inside of Mac apps and Windows exes. Right now, the only way to have a custom Mac icon is to convert your image to .icns format and put it in the resources folder of the app. For windows, you have to use a utility like Resource Hacker.

