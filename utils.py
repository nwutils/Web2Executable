"""Utility functions for Web2Executable

This module holds utility functions that are useful to both the command line
and GUI modules, but aren't related to either module.
"""
from __future__ import print_function
import os
import zipfile
import io
import platform
import urllib.request as request
import tempfile
import codecs
import shutil
import subprocess
from appdirs import AppDirs
import validators
import traceback
import logging
import config

from PySide6 import QtCore

logger = logging.getLogger(__name__)

def url_exists(path):
    if validators.url(path):
        return True
    return False

def format_exc_info(exc_info):
    """Return exception string with traceback"""
    exc_format = traceback.format_exception(exc_info[0],
                                            exc_info[1],
                                            exc_info[2])
    error = ''.join([x for x in exc_format])
    return error

def load_last_project_path():
    """Load the last open project.

    Returns:
        string: the last opened project path
    """
    proj_path = ''
    proj_file = get_data_file_path(config.LAST_PROJECT_FILE)
    if os.path.exists(proj_file):
        with codecs.open(proj_file, encoding='utf-8') as f:
            proj_path = f.read().strip()

    if not proj_path:
        proj_path = QtCore.QDir.currentPath()

    return proj_path

def load_recent_projects():
    """Load the most recent projects opened.

    Returns:
        list: project files sorted by most recent
    """
    files = []
    history_file = get_data_file_path(config.RECENT_FILES_FILE)
    if not os.path.exists(history_file):
        return files
    with codecs.open(history_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and os.path.exists(line):
                files.append(line)
    files.reverse()
    return files

def save_project_path(path):
    """Save the last open project path."""
    proj_file = get_data_file_path(config.LAST_PROJECT_FILE)
    with codecs.open(proj_file, 'w+', encoding='utf-8') as f:
        f.write(path)

def save_recent_project(proj):
    """Save the most recent projects to a text file."""
    recent_file_path = get_data_file_path(config.RECENT_FILES_FILE)
    max_length = config.MAX_RECENT
    recent_files = []
    if os.path.exists(recent_file_path):
        file_contents = codecs.open(recent_file_path, encoding='utf-8').read()
        recent_files = file_contents.split('\n')
    try:
        recent_files.remove(proj)
    except ValueError:
        pass
    recent_files.append(proj)
    with codecs.open(recent_file_path, 'w+', encoding='utf-8') as f:
        for recent_file in recent_files[-max_length:]:
            if recent_file and os.path.exists(recent_file):
                f.write('{}\n'.format(recent_file))


def replace_right(source, target, replacement, replacements=None):
    """
    String replace rightmost instance of a string.

    Args:
        source (string): the source to perform the replacement on
        target (string): the string to search for
        replacement (string): the replacement string
        replacements (int or None): if an integer, only replaces N occurrences
                                    otherwise only one occurrence is replaced
    """
    return replacement.join(source.rsplit(target, replacements))

def is_windows():
    return platform.system() == 'Windows'

def get_temp_dir():
    return tempfile.gettempdir()

## File operations ------------------------------------------------------
# These are overridden because shutil gets Windows directories confused
# and cannot write to them even if they are valid in cmd.exe

def path_join(base, *rest):
    new_rest = []
    for r in rest:
        new_rest.append(str(r))

    rpath = '/'.join(new_rest)

    if not os.path.isabs(rpath):
        rpath = base + '/' + rpath

    if is_windows():
        rpath = rpath.replace('/', '\\')

    rpath = os.path.normpath(rpath)

    return rpath

def get_data_path(dir_path):

    parts = dir_path.split('/')
    if config.TESTING:
        data_path = path_join(config.CWD, 'tests', 'test_data', *parts)
    else:
        dirs = AppDirs('Web2Executable', 'Web2Executable')
        data_path = path_join(dirs.user_data_dir, *parts)

    if is_windows():
        data_path = data_path.replace('\\', '/')

    if not os.path.exists(data_path):
        os.makedirs(data_path)

    return data_path

def abs_path(file_path):
    path = os.path.abspath(file_path)

    if is_windows():
        path = path.replace('/', '\\')

    return path

def get_data_file_path(file_path):
    parts = file_path.split('/')
    data_path = get_data_path('/'.join(parts[:-1]))
    return path_join(data_path, parts[-1])

def rmtree(path, **kwargs):
    if is_windows():
        if os.path.isabs(path):
            path = '\\\\?\\'+path.replace('/', '\\')
    shutil.rmtree(path, **kwargs)

def copy(src, dest, **kwargs):
    if is_windows():
        if os.path.isabs(src):
            src = '\\\\?\\'+src.replace('/', '\\')
        if os.path.isabs(dest):
            dest = '\\\\?\\'+dest.replace('/', '\\')
    shutil.copy2(src, dest, **kwargs)

def move(src, dest, **kwargs):
    if is_windows():
        if os.path.isabs(src):
            src = '\\\\?\\'+src.replace('/', '\\')
        if os.path.isabs(dest):
            dest = '\\\\?\\'+dest.replace('/', '\\')
    shutil.move(src, dest, **kwargs)

def copytree(src, dest, **kwargs):
    if is_windows():
        if os.path.isabs(src) and not src.startswith('\\\\'):
            src = '\\\\?\\'+src.replace('/', '\\')
        if os.path.isabs(dest) and not dest.startswith('\\\\'):
            dest = '\\\\?\\'+dest.replace('/', '\\')
    shutil.copytree(src, dest, **kwargs)

## ------------------------------------------------------------

def log(*args):
    """Print logging information or log it to a file."""
    if config.DEBUG:
        print(*args)
    logger.info(', '.join(args))

def open_folder_in_explorer(path):
    """Cross platform open folder window."""
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

def zip_files(zip_file_name, project_dir, *args, **kwargs):
    """
    Zip files into an archive programmatically.

    Args:
        zip_file_name (string): the name of the resulting zip file
        args: the files to zip
        kwargs: Options
            verbose (bool): if True, gives verbose output
            exclude_paths (list): a list of paths to exclude
    """
    zip_file = zipfile.ZipFile(zip_file_name, 'w', config.ZIP_MODE)
    verbose = kwargs.pop('verbose', False)
    old_path = os.getcwd()

    os.chdir(project_dir)

    for arg in args:
        if os.path.exists(arg):
            file_loc = arg
            if verbose:
                log(file_loc)
            try:
                zip_file.write(file_loc)
            except ValueError:
                os.utime(file_loc, None)
                zip_file.write(file_loc)

    os.chdir(old_path)

    zip_file.close()

def join_files(destination, *args, **kwargs):
    """
    Join any number of files together by stitching bytes together.

    This is used to take advantage of NW.js's ability to execute a zip file
    contained at the end of the exe file.

    Args:
        destination (string): the name of the resulting file
        args: the files to stitch together
    """
    with io.open(destination, 'wb') as dest_file:
        for arg in args:
            if os.path.exists(arg):
                with io.open(arg, 'rb') as file:
                    while True:
                        bytes = file.read(4096)
                        if len(bytes) == 0:
                            break
                        dest_file.write(bytes)

def urlopen(url):
    """
    Call urllib.request.urlopen with a modified SSL context to prevent
    "SSL: CERTIFICATE_VERIFY_FAILED” errors when no verification is
    actually needed.
    """
    return request.urlopen(url, context=config.SSL_CONTEXT)

# To avoid a circular import, we import config at the bottom of the file
# and reference it on the module level from within the functions
import config
