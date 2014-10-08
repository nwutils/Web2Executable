Web2Executable
==============

Uses node-webkit to generate "native" apps for already existing web apps.

Requires the pyside library and python 2.X to run. I've only tested the code on python 2.7.3-2.7.5, so I can't speak about any lower version, but it should work as long as PySide is supported.

If you liked this project that I've committed many hours to, show whatever support you wish as a donation here: 

<a href='https://pledgie.com/campaigns/26899'><img alt='Click here to lend your support to: Web2Executable Donations and make a donation at pledgie.com !' src='https://pledgie.com/campaigns/26899.png?skin_name=chrome' border='0' ></a>

Note!!
------

When building linux applications using this application, there is an issue on the newer versions of Ubuntu (13.XX) and similar distros that causes the error: Shared library libudev.so.0 does not exist. If you are distributing an application by exporting to these platforms, you'll need to instruct your users to either manually symlink the file or make an install script following the directions [here](https://github.com/rogerwang/node-webkit/wiki/The-solution-of-lacking-libudev.so.0). This is an issue with node-webkit and not this application itself.

Also, there was an issue for Mac with versions older that 0.1.8b where it wouldn't start up. Hopefully that is fixed now and you can enjoy the app!

Getting Started
---------------

Run with:

```
python main.py
```

It's a pretty simple app. Just point it the the directory that your web application lives, customize the options (the two marked with a star are the only ones required) and then choose your export options. The app will export under YOUR_OUTPUT_DIR/YOUR_APP_NAME. 

What's New?
----------------------

v0.1.8b
- added an "Open to export folder" button that makes things a little easier to navigate to.
- attempted to fix Mac OS X issues with crashing

v0.1.7b
- added better download management so there is no redownloading things. Also a bunch of bugs were fixed up.

v0.1.6b

- added the ability to get newer NodeWebkit versions automatically from the changelog of node-webkit. Also fixed compatibility with 0.10.X.

v0.1.4b

- fixed an issue where index.html would be found with absolute path, which would cause a "require not found" error

v0.1.3b

- Added the ability to choose node-webkit versions if 0.9.2 is not what you want*
- Modified the UI slightly for people with smaller monitors
- Added a force-download option to overwrite files

*Note: If you have already downloaded, say, 0.9.2 of webkit, then you select 0.8.5, you will have to select "Force download" in order to update the files properly. I'm not sure how to reliably/efficiently detect and store multiple versions of the node-webkit files.

v0.1.2b

- Fixed an issue with icon copying
- Fixed a bug that overwrote existing package.json files.

Prebuilt Binaries
-----------------

###Mac OS X

[Mac OS X 10.7+ download - v0.1.8b](http://www.mediafire.com/download/jpkygqrlpj4rnu9/Web2Executable-v0.1.8b.zip)

Previous Version:

[Mac OS X 10.7+ download - v0.1.5b](http://www.mediafire.com/download/lpd33ttatgvfrbn/Web2ExeMac-v0.1.5b.zip)


You can just put the app where ever you want and double click to run it.

###Windows

[Windows 7+ download - v0.1.8b](http://www.mediafire.com/download/cgpqdh8e5w9p31m/Web2ExeWin-v0.1.8b.zip)


Previous Version:

[Windows 7+ download - v0.1.7b](http://www.mediafire.com/download/2rw62cr92n313ai/Web2ExeWin-v0.1.7b.zip)




Double click the Win2Exe.exe file inside the extracted folder.

###Linux

Only on Ubuntu 12.04. If someone knows how to make them on all linux distros, let me know. I'm using cx_Freeze to compile them to standalone apps. You must copy all .so.X.X files to either /usr/local/lib/ or /usr/lib/ for it to work.


[Linux 64bit download - v0.1.7b](http://www.mediafire.com/download/4cujo6qdjzr337f/Web2ExeLinux64-v0.1.7b.zip)

Previous Version:

[Linux 64bit download - v0.1.6b](http://www.mediafire.com/download/7iozo8tfbn6rea8/Web2ExeLinux64-v0.1.6b.zip)


chmod 755 the main binary inside the extracted folder and then run by double clicking or ./main from the command line. Also, if you get shared library errors, you need to copy all the .so files into /usr/lib/ or /usr/local/lib/. Make sure you check to see if any libraries in /usr/lib/ conflict with the files first.

```
chmod 755 main
sudo cp *.so.* /usr/lib/
```

Note: For some reason, these linux binaries are not working correctly on vanilla systems. I'm looking into the issue and will update them when I figure out what is going on.


Features
--------

- Cross platform to Mac, Windows, Linux
- Easy to use and straightforward
- Streamlined workflow from project -> working standalone exe
- Same performance as Google Chrome
- Works with Phaser; should work with other HTML5 game libraries
- Export web applications to all platforms from your current OS
- Ability to specify a node-webkit version to download

Future Features
---------------

- A download manager! It's getting annoying downloading stuff over and over.
- Automatic replacement of icon files inside of Mac apps and Windows exes. Right now, the only way to have a custom Mac icon is to convert your image to .icns format and put it in the resources folder of the app. For windows, you have to use a utility like Resource Hacker.


Screenshots
-----------

v0.1.3b

![Screenshot2](http://i.imgur.com/jZ7TE63.png)

v0.1.2b

![Screenshot](http://i.imgur.com/V1609ea.png) 


