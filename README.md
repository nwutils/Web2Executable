[![Github Releases (by Release)](https://img.shields.io/github/downloads/jyapayne/Web2Executable/v0.5.0b/total.svg?maxAge=2592000)]()

[![Github All Releases](https://img.shields.io/github/downloads/jyapayne/Web2Executable/total.svg?maxAge=2592000)]()

Web2Executable
==============

[Releases (Downloads)](https://github.com/jyapayne/Web2Executable/releases) (new!)


What is it?
-----------

Web2Executable is a friendly command line and GUI application that can transform your Nodejs (or any other JS/HTML) app into a standalone executable. It can export to Mac OS X, Windows and Linux all from one platform, so no need to go out and buy expensive hardware.

It's powered by the very awesome project [NWJS](https://github.com/nwjs) and PySide, is open source, and is just dang awesome and easy to use.

If you have an idea for a feature, please create a new issue with a format like this: "Feature - My Awesome New Feature", along with a good description of what you'd like the feature to do.

If you got some value out of using my app, consider donating a dollar to keep me caffeinated :) 

<a href='https://pledgie.com/campaigns/26899'><img alt='Click here to lend your support to: Web2Executable Donations and make a donation at pledgie.com !' src='https://pledgie.com/campaigns/26899.png?skin_name=chrome' border='0' ></a>

On the other hand, if you have any annoyances with the application and want to contribute to making it better for everyone, please file an issue with "Annoyance:" as the first part of the title. Sometimes it's hard to know what is annoying for people and input is much appreciated :)

What About Electron?
--------------------

If you want to export using Electron instead of NW.js, try [Electrify](https://github.com/jyapayne/Electrify), my other app based on Web2Executable.


Who's Using It?
---------------

Lots of people! There are currently thousands of downloads and several articles written about using Web2Executable.

Some articles include:

[Getting a Phaser Game on Steam](http://phaser.io/news/2015/10/getting-a-phaser-game-on-steam)

[Packt Publishing NW.js Essentials Tutorial](https://www.packtpub.com/packtlib/book/Web-Development/9781785280863/7/ch07lvl1sec53/Web2Executable) and [Ebook](https://books.google.ca/books?id=wz6qCQAAQBAJ&pg=PA135&lpg=PA135&dq=web2executable&source=bl&ots=sPP-3BOMXX&sig=UolyF31WcTgA-lrel2UTIfzs65U&hl=en&sa=X&redir_esc=y#v=onepage&q=web2executable&f=false)

[A Russian NW.js Tutoral](http://canonium.com/articles/nwjs-web-to-executable)

[Marv's Blog](http://www.marv.ph/tag/web2exe/)

[Shotten.com Node-webkit for Poets](http://www.shotton.com/wp/2014/10/27/node-webkit-for-poets-mac-version/)

If you have a project you'd like to see listed here that was successfully built using Web2Executable or you have written an article that mentions it, feel free to send me an email with a link and I'd be super stoked to paste it here :)


Features
--------

- Cross platform to Mac, Windows, Linux
- Working media out of the box (sound and video)
- Easy to use and straightforward
- Streamlined workflow from project -> working standalone exe
- Same performance as Google Chrome
- Works with Phaser; should work with other HTML5 game libraries
- Export web applications to all platforms from your current OS
- Ability to specify a node-webkit version to download
- Automatic insertion of icon files into Windows exe's or Mac Apps by filling out the icon fields as necessary
- A command line utility with functionality equivalent to the GUI. Useful for automated builds.
- Compression of executables with upx

Planned New Features
--------------------

- The ability to add external files to the project
- Minifying JS and HTML


Getting Started
---------------

###Using Prebuilt Binaries

When using the prebuilt binaries for Windows, Mac, or Ubuntu, there are NO dependencies or extra applications needed. Simply download Web2Exe for the platform of your choice, extract, and double click the app/exe/binary to start. This applies to both the command-line version and the GUI version.

**NOTE!**: Some people report needing the Microsoft Visual C++ 2008/2010 SP1 and regular Redistributable package. I don't have a machine to test this, but just know that you might need the package if the application won't open or spits out the following error:

```
Error: The application has failed to start because the side by side configuration is incorrect please see the application event log or use the command line sxstrace.exe tool for more detail.
```


### Run from Python Source

Requires the PySide library and Python 3.4.3 or higher. If you want to replace the icon in the Windows Exe's, this will do it automatically with the latest code if you have PIL or Pillow installed.
####GUI

Install dependencies:

```
pip install -r requirements.txt
```

Initiate submodules:

```
git submodule update --init --recursive
```

Run with:

```
python3.4 main.py
```

It's a pretty simple app. Just point it to the directory where your web application lives, customize the options (the two marked with a star are the only ones required) and then choose your export options. The app will export under YOUR_OUTPUT_DIR/YOUR_APP_NAME. 

####Command line interface

Dependencies: configobj (install with pip) and Pillow if you want icon replacement (not necessary)

Run the command_line.py with the --help option to see a list of export options. Optionally, if you don't want to install python, there are builds for Mac and Windows in the command_line_builds folder of this repository.

Example usage (if using the prebuilt binary, replace `python3.4 command_line.py` with the exe name):

```
python3.4 command_line.py /var/www/html/CargoBlaster/ --main html/index.html --export-to linux-x64 windows mac --width 900 --height 700 --nw-version 0.10.5
```

###GUI Instructions

To use Web2Exe:
  1. Choose a project folder with at least one html or php file. The name of the export application will be autogenerated from the folder that you choose, so change it if you so desire.
  2. Modify the options as needed.
  3. Choose at least one export platform and then the Export button should enable (as long as the field names marked with a star are filled out and all files in the fields exist).
  4. Click the export button and once it's done, click the "Open Export Folder" button to go to the folder where your exported project will be.


### Issues?

If you have an issue, please check the FAQ before filing an issue to see if it helps.

[FAQ](https://github.com/jyapayne/Web2Executable/wiki/FAQ)


### Additional Info

[Changelog](https://github.com/jyapayne/Web2Executable/releases)

[Screenshots](https://github.com/jyapayne/Web2Executable/wiki/Screenshots)


License
-------

The MIT License (MIT)

Copyright (c) 2015 SimplyPixelated

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
