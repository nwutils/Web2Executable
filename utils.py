from __future__ import print_function
import os, zipfile, io, platform
import sys, tempfile
import subprocess

try:
    import zlib
    ZIP_MODE = zipfile.ZIP_DEFLATED
except:
    ZIP_MODE = zipfile.ZIP_STORED

DEBUG = False

def is_windows():
    return platform.system() == 'Windows'

def get_temp_dir():
    return tempfile.gettempdir()

def log(*args):
    if DEBUG:
        print(*args)

def open_folder_in_explorer(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

def zip_files(zip_file_name, *args, **kwargs):
    zip_file = zipfile.ZipFile(zip_file_name, 'w', ZIP_MODE)
    verbose = kwargs.pop('verbose', False)
    exclude_paths = kwargs.pop('exclude_paths', [])
    old_path = os.getcwd()

    for arg in args:
        if os.path.exists(arg):
            if os.path.isdir(arg):
                directory = os.path.abspath(arg)
                os.chdir(directory)

                for root, dirs, files in os.walk(directory):
                    excluded = False
                    for exclude_path in exclude_paths:
                        if exclude_path in os.path.join(directory,root):
                            excluded = True
                    if not excluded:
                        for file in files:
                            file_loc = os.path.relpath(os.path.join(root, file), directory)
                            if verbose:
                                log(file_loc)
                            zip_file.write(file_loc)
                        for direc in dirs:
                            dir_loc = os.path.relpath(os.path.join(root, direc), directory)
                            if verbose:
                                log(dir_loc)
                            zip_file.write(dir_loc)

            else:
                file = os.path.abspath(arg)
                directory = os.path.abspath(os.path.join(file, '..'))
                os.chdir(directory)
                file_loc = os.path.relpath(arg, directory)
                if verbose:
                    log(file_loc)
                zip_file.write(file_loc)

    os.chdir(old_path)

    zip_file.close()

def join_files(destination, *args, **kwargs):
    with io.open(destination, 'wb') as dest_file:
        for arg in args:
            if os.path.exists(arg):
                with io.open(arg, 'rb') as file:
                    while True:
                        bytes = file.read(4096)
                        if len(bytes) == 0:
                            break
                        dest_file.write(bytes)
