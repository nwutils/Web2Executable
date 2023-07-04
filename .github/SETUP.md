#Setup Guide

In order to run Web2Executable from Python code to make modifications to this repo, you'll need to install a few prerequisites first.

##Prerequisites

###Qt 4.8.7

Download and install Qt 4.8.7 from [here](https://download.qt.io/official_releases/qt/4.8/4.8.7/) or from your package manager. PySide uses Qt 4.8.X and is incompatible with Qt 5 and higher.

For Mac OSX, it might be needed to install the latest 4.8.X version via compiling the source. Download the `qt-everywhere-opensource-src-4.8.X` version and run the following in the extracted directory:

```
./configure
make
sudo make install
```

Alternatively, you may wish to install it via homebrew if you have it installed:

```
brew install qt
```

###Python 3.4

Download and install the latest Python3.4.X release from the Python website. Python 3.5 and higher may work, but this repo was only tested with Python 3.4.

###System requirements

If you want to use the conversion of any image to icns and png using Pillow, you must install some libraries.

libjpeg, libpng, openjpeg

###Pip Requirements

Install pip requirements with

```
pip install -r requirements.txt
```

##Running

Once all of the above are installed, simply run:

```
python3.4 main.py
```

##Tests

Tests are located in the tests directory and were created with pytest.
They can be run with:

```
pytest
```

in the root directory.
