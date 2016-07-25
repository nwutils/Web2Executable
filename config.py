from __future__ import print_function
import os
import logging
import logging.handlers as lh
import traceback
import sys
import zipfile

import utils


ZIP_MODE = zipfile.ZIP_STORED

MAX_RECENT = 10

DEBUG = False

### The following sections are code that needs to be run when importing
### from main.py.

## CWD Computation --------------------------------------

inside_packed_exe = getattr(sys, 'frozen', '')

if inside_packed_exe:
    # we are running in a |PyInstaller| bundle
    CWD = os.path.dirname(sys.executable)
else:
    # we are running in a normal Python environment
    CWD = os.path.dirname(os.path.realpath(__file__))

## CMD Utility functions --------------------------------

def get_file(path):
    parts = path.split('/')
    independent_path = utils.path_join(CWD, *parts)
    return independent_path

def is_installed():
    uninst = get_file('uninst.exe')
    return utils.is_windows() and os.path.exists(uninst)

## Version Setting ----------------------------------------

__version__ = "v0.0.0"

with open(get_file('files/version.txt')) as f:
    __version__ = f.read().strip()


TEMP_DIR = utils.get_temp_dir()
DEFAULT_DOWNLOAD_PATH = utils.get_data_path('files/downloads')

## Logger setup ----------------------------------------------

logger = logging.getLogger('W2E logger')
LOG_FILENAME = utils.get_data_file_path('files/error.log')
if __name__ != '__main__':
    logging.basicConfig(
        filename=LOG_FILENAME,
        format=("%(levelname) -10s %(asctime)s %(module)s.py: "
                "%(lineno)s %(funcName)s - %(message)s"),
        level=logging.DEBUG
    )
    logger = logging.getLogger('W2E logger')

handler = lh.RotatingFileHandler(LOG_FILENAME, maxBytes=100000, backupCount=2)
logger.addHandler(handler)

## Custom except hook to log all errors ----------------------

def my_excepthook(type_, value, tback):
    output_err = u''.join([x for x in traceback.format_exception(type_, value, tback)])
    logger.error(u'{}'.format(output_err))
    sys.__excepthook__(type_, value, tback)

sys.excepthook = my_excepthook


# Ensure that the default download path exists
try:
    os.makedirs(DEFAULT_DOWNLOAD_PATH)
except:
    pass
