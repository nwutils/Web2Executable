"""
Configuration module that holds some configuration options for
Web2Executable.
"""

from __future__ import print_function
import os
import logging
import logging.handlers as lh
import traceback
import sys
import zipfile
import ssl

import utils

ZIP_MODE = zipfile.ZIP_STORED

MAX_RECENT = 10

DEBUG = False
TESTING = False

SSL_CONTEXT = ssl._create_unverified_context()

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

ICON_PATH = 'files/images/icon.png'
WARNING_ICON = 'files/images/warning.png'
APP_SETTINGS_ICON = 'files/images/app_settings.png'
WINDOW_SETTINGS_ICON = 'files/images/window_settings.png'
EXPORT_SETTINGS_ICON = 'files/images/export_settings.png'
COMPRESS_SETTINGS_ICON = 'files/images/compress_settings.png'
DOWNLOAD_SETTINGS_ICON = 'files/images/download_settings.png'
FOLDER_OPEN_ICON = 'files/images/folder_open.png'

W2E_VER_FILE = 'files/version.txt'

TEMP_DIR = utils.get_temp_dir()

ERROR_LOG_FILE = 'files/error.log'
VER_FILE = 'files/nw-versions.txt'
SETTINGS_FILE = 'files/settings.cfg'
GLOBAL_JSON_FILE = 'files/global.json'
WEB2EXE_JSON_FILE = 'web2exe.json'

LAST_PROJECT_FILE = 'files/last_project_path.txt'
RECENT_FILES_FILE = 'files/recent_files.txt'

NW_BRANCH_FILE = 'files/nw-branch.txt'

UPX_WIN_PATH = 'files/compressors/upx-win.exe'
UPX_MAC_PATH = 'files/compressors/upx-mac'
UPX_LIN32_PATH = 'files/compressors/upx-linux-x32'
UPX_LIN64_PATH = 'files/compressors/upx-linux-x64'

ENV_VARS_PY_PATH = 'files/env_vars.py'
ENV_VARS_BAT_PATH = 'files/env_vars.bat'
ENV_VARS_BASH_PATH = 'files/env_vars.bash'

## Logger setup ----------------------------------------------

LOG_FILENAME = utils.get_data_file_path(ERROR_LOG_FILE)

if DEBUG:
    logging.basicConfig(
        filename=LOG_FILENAME,
        format=("%(levelname) -10s %(asctime)s %(module)s.py: "
                "%(lineno)s %(funcName)s - %(message)s"),
        level=logging.DEBUG
    )
else:
    logging.basicConfig(
        filename=LOG_FILENAME,
        format=("%(levelname) -10s %(asctime)s %(module)s.py: "
                "%(lineno)s %(funcName)s - %(message)s"),
        level=logging.INFO
    )



def getLogger(name):
    logger = logging.getLogger(name)
    handler = lh.RotatingFileHandler(LOG_FILENAME,
                                     maxBytes=100000,
                                     backupCount=2)
    logger.addHandler(handler)
    return logger


logger = getLogger(__name__)


## Custom except hook to log all errors ----------------------

def my_excepthook(type_, value, tback):
    output_err = ''.join([x for x in traceback.format_exception(type_, value,
                                                                tback)])
    logger.error('{}'.format(output_err))
    sys.__excepthook__(type_, value, tback)

sys.excepthook = my_excepthook

def download_path(path=None):
    # Ensure that the default download path exists
    path = path or utils.get_data_path('files/downloads')
    try:
        os.makedirs(path)
    except:
        pass
    return path
