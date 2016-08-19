from __future__ import print_function
import os
import zipfile
import io
import platform
import tempfile
import codecs
import shutil
import subprocess
from appdirs import AppDirs
import validators

from PySide import QtCore

#try:
#    import zlib
#    ZIP_MODE = zipfile.ZIP_DEFLATED
#except:


def url_exists(path):
    if validators.url(path):
        return True
    return False

def load_last_project_path():
    proj_path = ''
    proj_file = get_data_file_path('files/last_project_path.txt')
    if os.path.exists(proj_file):
        with codecs.open(proj_file, encoding='utf-8') as f:
            proj_path = f.read().strip()

    if not proj_path:
        proj_path = QtCore.QDir.currentPath()

    return proj_path

def load_recent_projects():
    files = []
    history_file = get_data_file_path('files/recent_files.txt')
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
    proj_file = get_data_file_path('files/last_project_path.txt')
    with codecs.open(proj_file, 'w+', encoding='utf-8') as f:
        f.write(path)

def save_recent_project(proj):
    recent_file_path = get_data_file_path('files/recent_files.txt')
    max_length = config.MAX_RECENT
    recent_files = []
    if os.path.exists(recent_file_path):
        recent_files = codecs.open(recent_file_path, encoding='utf-8').read().split(u'\n')
    try:
        recent_files.remove(proj)
    except ValueError:
        pass
    recent_files.append(proj)
    with codecs.open(recent_file_path, 'w+', encoding='utf-8') as f:
        for recent_file in recent_files[-max_length:]:
            if recent_file and os.path.exists(recent_file):
                f.write(u'{}\n'.format(recent_file))


def replace_right(source, target, replacement, replacements=None):
    return replacement.join(source.rsplit(target, replacements))

def is_windows():
    return platform.system() == 'Windows'

def get_temp_dir():
    return tempfile.gettempdir()

def path_join(base, *rest):
    new_rest = []
    for i in range(len(rest)):
        new_rest.append(str(rest[i]))

    rpath = u'/'.join(new_rest)

    if not os.path.isabs(rpath):
        rpath = base + u'/' + rpath

    if is_windows():
        rpath = rpath.replace('/', '\\')
    return rpath

def get_data_path(dir_path):
    parts = dir_path.split('/')
    dirs = AppDirs('Web2Executable', 'Web2Executable')
    data_path = path_join(dirs.user_data_dir, *parts)

    if is_windows():
        data_path = data_path.replace(u'\\', u'/')

    if not os.path.exists(data_path):
        os.makedirs(data_path)

    return data_path

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
        if os.path.isabs(src):
            src = '\\\\?\\'+src.replace('/', '\\')
        if os.path.isabs(dest):
            dest = '\\\\?\\'+dest.replace('/', '\\')
    shutil.copytree(src, dest, **kwargs)

def log(*args):
    if config.DEBUG:
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
    zip_file = zipfile.ZipFile(zip_file_name, 'w', config.ZIP_MODE)
    verbose = kwargs.pop('verbose', False)
    exclude_paths = kwargs.pop('exclude_paths', [])
    old_path = os.getcwd()

    for arg in args:
        if is_windows():
            arg = '\\\\?\\'+os.path.abspath(arg).replace('/', '\\')
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
                            except FileNotFoundError:
                                pass
                        for direc in dirs:
                            dir_loc = os.path.relpath(path_join(root, direc), directory)
                            if verbose:
                                log(dir_loc)
                            try:
                                zip_file.write(dir_loc)
                            except ValueError:
                                os.utime(file_loc, None)
                                zip_file.write(file_loc)
                            except FileNotFoundError:
                                pass

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


import config

