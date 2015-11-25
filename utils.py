from __future__ import print_function
import os, zipfile, io, platform
import sys, tempfile
import subprocess
from appdirs import AppDirs

#try:
#    import zlib
#    ZIP_MODE = zipfile.ZIP_DEFLATED
#except:
ZIP_MODE = zipfile.ZIP_STORED

DEBUG = False

def is_windows():
    return platform.system() == 'Windows'

def get_temp_dir():
    return tempfile.gettempdir()

def path_join(base, *rest):
    try:
        base = base.decode('utf-8')
    except UnicodeEncodeError:
        base = unicode(base)
    new_rest = []
    for i in xrange(len(rest)):
        try:
            new_rest.append(rest[i].decode('utf-8'))
        except UnicodeEncodeError:
            new_rest.append(unicode(rest[i]))
    rpath = u'/'.join(new_rest)
    if os.path.isabs(rpath):
        return rpath
    else:
        return base + u'/' + rpath

def get_data_path(dir_path):
    parts = dir_path.split('/')
    dirs = AppDirs('Web2Executable', 'Web2Executable')
    data_path = path_join(dirs.user_data_dir, *parts)
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    return data_path

def get_data_file_path(file_path):
    parts = file_path.split('/')
    data_path = get_data_path('/'.join(parts[:-1]))
    return path_join(data_path, parts[-1])

def log(*args):
    if DEBUG:
        print(*args)
    with open(get_data_file_path('files/error.log'), 'a+') as f:
        f.write(', '.join(args))
        f.write('\n')

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
                        if exclude_path in path_join(directory,root):
                            excluded = True
                    if not excluded:
                        for file in files:
                            file_loc = os.path.relpath(path_join(root, file), directory)
                            if verbose:
                                log(file_loc)
                            try:
                                zip_file.write(file_loc)
                            except ValueError:
                                os.utime(file_loc, None)
                                zip_file.write(file_loc)
                        for direc in dirs:
                            dir_loc = os.path.relpath(path_join(root, direc), directory)
                            if verbose:
                                log(dir_loc)
                            try:
                                zip_file.write(dir_loc)
                            except ValueError:
                                os.utime(file_loc, None)
                                zip_file.write(file_loc)

            else:
                file = os.path.abspath(arg)
                directory = os.path.abspath(path_join(file, '..'))
                os.chdir(directory)
                file_loc = os.path.relpath(arg, directory)
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
    with io.open(destination, 'wb') as dest_file:
        for arg in args:
            if os.path.exists(arg):
                with io.open(arg, 'rb') as file:
                    while True:
                        bytes = file.read(4096)
                        if len(bytes) == 0:
                            break
                        dest_file.write(bytes)
