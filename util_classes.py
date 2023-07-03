"""Utility classes that are used both in the GUI and the CMD."""

import os
import re
from fnmatch import fnmatch
import zipfile
import tarfile
import time
import logging
from pprint import pformat

import config
import utils

from PySide6 import QtGui, QtCore
from PySide6 import QtWidgets
from PySide6.QtCore import Qt


class FileItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent=None, path=None):
        super(FileItem, self).__init__(parent)
        self.path = path


class FileTree(object):
    def __init__(self, directory=None,
                 whitelist=None, blacklist=None):

        self.whitelist = None
        self.blacklist = None

        self.paths = []
        self.walkcache = {}
        self.cache = True
        self.time = time.time()

        self.files = []
        self.dirs = []

        self.init(directory, whitelist, blacklist)

    def init(self, directory=None,
             whitelist=None, blacklist=None):

        self.logger = config.getLogger(__name__)

        if directory:
            self.directory = directory + os.sep
        else:
            self.directory = directory

        self.refresh(whitelist, blacklist)

    def clear(self):
        self.files = []
        self.dirs = []

    def refresh(self, whitelist=None,
                blacklist=None):
        self.set_filters(whitelist, blacklist)

        self.clear()

        self.generate_files()

    def walk(self, directory):
        refresh = False

        if (time.time() - self.time) > 10:
            refresh = True
            self.time = time.time()

        if not self.walkcache.get(directory) or refresh:
            self.walkcache[directory] = []
            return os.walk(directory)

        return self.walkcache[directory]

    def determine_skip(self, path, *args, **kwargs):
        skip = False

        for blacklist in self.blacklist:
            match = fnmatch(path, blacklist)
            if match:
                skip = True
                self.on_blacklist_match(path, *args, **kwargs)
                break

        for whitelist in self.whitelist:
            match = fnmatch(path, whitelist)
            if match:
                skip = False
                self.on_whitelist_match(path, *args, **kwargs)
                break

        return skip

    def set_filters(self, whitelist=None, blacklist=None):
        self.whitelist = whitelist or self.whitelist or []
        self.blacklist = blacklist or self.blacklist or []

    def on_whitelist_match(self, path, *args, **kwargs):
        pass

    def on_blacklist_match(self, path, *args, **kwargs):
        pass

    def init_cache(self):
        if self.walkcache.get(self.directory) is None:
            self.walkcache[self.directory] = []

        self.cache = False
        if not self.walkcache[self.directory]:
            self.cache = True

    def add_to_cache(self, *args):
        if self.cache:
            self.walkcache[self.directory].append(args)

    def is_in_skipped(self, skipped, path):
        temp = path

        while temp:
            if temp in skipped:
                return True
            if temp == os.path.dirname(temp):
                return False
            temp = os.path.dirname(temp)
        return False

    def generate_files(self):
        if self.directory is None:
            return

        self.logger.debug('Blacklist pattern:')
        self.logger.debug(pformat(self.blacklist))
        self.logger.debug('')
        self.logger.debug('Whitelist pattern:')
        self.logger.debug(pformat(self.whitelist))
        self.logger.debug('')

        self.init_cache()

        skipped_files = set()

        for root, dirs, files in self.walk(self.directory):
            self.add_to_cache(root, dirs, files)

            proj_path = root.replace(self.directory, '')

            for directory in dirs:
                path = os.path.join(proj_path, directory)

                if self.determine_skip(path):
                    if not self.is_in_skipped(skipped_files, path):
                        self.logger.debug('Skipping dir: %s', path)
                    skipped_files.add(path)
                    continue
                else:
                    if self.is_in_skipped(skipped_files, path):
                        self.logger.debug('Keeping dir: %s', path)

                self.dirs.append(path)

            for file in files:
                path = os.path.join(proj_path, file)

                if self.determine_skip(path):
                    if not self.is_in_skipped(skipped_files, path):
                        self.logger.debug('Skipping file: %s', path)
                    skipped_files.add(path)
                    continue
                else:
                    if self.is_in_skipped(skipped_files, path):
                        self.logger.debug('Keeping file: %s', path)

                self.files.append(path)


class TreeBrowser(QtWidgets.QWidget):
    def __init__(self, directory=None,
                 whitelist=None, blacklist=None, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.root = QtWidgets.QTreeWidget()
        self.root.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.root.header().setStretchLastSection(False)
        self.root.setHeaderLabel('Included files')

        self.parent_map = {}

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.root)
        self.setLayout(layout)

        self.file_tree = FileTree(directory, whitelist, blacklist)
        self.init(directory, whitelist, blacklist)

    def clear(self):
        self.root.clear()
        self.file_tree.clear()

    def init(self, directory=None,
             whitelist=None, blacklist=None):

        self.file_tree.init(directory, whitelist, blacklist)

        self.refresh(whitelist, blacklist)

    def refresh(self, whitelist=None,
                blacklist=None):
        self.file_tree.set_filters(whitelist, blacklist)
        self.clear()
        self.generate_files()

    def fix_tree(self, path, parent):
        temp = parent
        tree = []
        root = None
        base, direc = os.path.split(path)
        new_path = os.path.join(base, direc)

        while new_path and root is None:
            temp = self.parent_map.get(os.path.join(base, direc))
            if temp is not None:
                root = temp
                break

            child = FileItem(None, os.path.join(base, direc))
            child.setText(0, direc)

            tree.insert(0, child)
            base, direc = os.path.split(base)
            new_path = os.path.join(base, direc)

            self.parent_map[child.path] = child

        # if we reached the top of the directory chain
        if root is None:
            # if the path is still valid, that means we need to create
            # a new top level item
            if new_path:
                root = FileItem(None, new_path)
                root.setText(0, direc)
                self.parent_map[root.path] = root
            else:
                # otherwise, the if the path is empty, we already
                # have a top level item, so use that
                root = tree.pop(0)

            self.root.addTopLevelItem(root)

        # add all the children to the root node
        temp = root
        for child in tree:
            temp.addChild(child)
            temp = child

    def on_whitelist_match(self, path, parent=None):
        if parent is None:
            self.fix_tree(path, parent)

    def generate_files(self):
        directory = self.file_tree.directory

        if directory is None:
            return

        self.parent_map = {'': self.root}

        self.file_tree.init_cache()

        for root, dirs, files in self.file_tree.walk(directory):
            self.file_tree.add_to_cache(root, dirs, files)

            proj_path = root.replace(directory, '')

            for dir in dirs:
                parent = self.parent_map.get(proj_path)

                path = os.path.join(proj_path, dir)

                if self.file_tree.determine_skip(path, parent=parent) or parent is None:
                    continue

                child = FileItem(parent, path)
                child.setText(0, dir)
                self.parent_map[path] = child
                self.file_tree.dirs.append(path)

            for file in files:
                parent = self.parent_map.get(proj_path)

                path = os.path.join(proj_path, file)

                if self.file_tree.determine_skip(path, parent=parent) or parent is None:
                    continue

                child = FileItem(parent, path)
                child.setText(0, file)
                self.file_tree.files.append(path)

        self.root.sortItems(0, Qt.AscendingOrder)


class ExistingProjectDialog(QtWidgets.QDialog):
    def __init__(self, recent_projects, directory_callback, parent=None):
        super(ExistingProjectDialog, self).__init__(parent)
        self.setWindowTitle('Open Project Folder')
        self.setWindowIcon(QtGui.QIcon(config.get_file('files/images/icon.png')))
        self.setMinimumWidth(500)

        group_box = QtWidgets.QGroupBox('Existing Projects')
        gbox_layout = QtWidgets.QVBoxLayout()
        self.project_list = QtWidgets.QListWidget()

        gbox_layout.addWidget(self.project_list)
        group_box.setLayout(gbox_layout)

        self.callback = directory_callback

        self.projects = recent_projects

        for project in recent_projects:
            text = '{} - {}'.format(os.path.basename(project), project)
            self.project_list.addItem(text)

        self.project_list.itemClicked.connect(self.project_clicked)

        self.cancel = QtWidgets.QPushButton('Cancel')
        self.open = QtWidgets.QPushButton('Open Selected')
        self.open_readonly = QtWidgets.QPushButton('Open Read-only')
        self.browse = QtWidgets.QPushButton('Browse...')

        self.open.setEnabled(False)
        self.open.clicked.connect(self.open_clicked)

        self.open_readonly.setEnabled(False)
        self.open_readonly.clicked.connect(self.open_readonly_clicked)

        self.browse.clicked.connect(self.browse_clicked)

        buttons = QtWidgets.QWidget()

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.cancel)
        button_layout.addWidget(QtWidgets.QWidget())
        button_layout.addWidget(self.browse)
        button_layout.addWidget(self.open_readonly)
        button_layout.addWidget(self.open)

        buttons.setLayout(button_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(group_box)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.cancel.clicked.connect(self.cancelled)

    def browse_clicked(self):

        default = self.parent().project_dir() or self.parent().last_project_dir

        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Find Project Directory',
                                                           default)

        if directory:
            self.callback(directory)
            self.close()

    def open_clicked(self):
        pos = self.project_list.currentRow()
        self.callback(self.projects[pos])
        self.close()

    def open_readonly_clicked(self):
        pos = self.project_list.currentRow()
        self.callback(self.projects[pos], readonly=True)
        self.close()

    def project_clicked(self, _):
        self.open.setEnabled(True)
        self.open_readonly.setEnabled(True)

    def cancelled(self):
        self.close()


class Validator(QtGui.QRegularExpressionValidator):
    def __init__(self, regex, action, parent=None):
        self.exp = regex
        self.action = str
        if hasattr(str, action):
            self.action = getattr(str, action)
        reg = QtCore.QRegularExpression(regex)
        super(Validator, self).__init__(reg, parent)

    def validate(self, text, pos):
        result = super(Validator, self).validate(text, pos)
        return result

    def fixup(self, text):
        return ''.join(re.findall(self.exp, self.action(text)))


class BackgroundThread(QtCore.QThread):
    def __init__(self, widget, method_name, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.widget = widget
        self.method_name = method_name

    def run(self):
        if hasattr(self.widget, self.method_name):
            func = getattr(self.widget, self.method_name)
            func()

class Setting(object):
    """Class that describes a setting from the setting.cfg file"""
    def __init__(self, name='', display_name=None, value=None,
                 required=False, type=None, file_types=None, *args, **kwargs):
        self.name = name
        self.display_name = (display_name
                             if display_name
                             else name.replace('_', ' ').capitalize())
        self.value = value
        self.last_value = None
        self.required = required
        self.type = type
        self.url = kwargs.pop('url', '')
        self.copy = kwargs.pop('copy', True)
        self.file_types = file_types
        self.scope = kwargs.pop('scope', 'local')

        self.default_value = kwargs.pop('default_value', None)
        self.button = kwargs.pop('button', None)
        self.button_callback = kwargs.pop('button_callback', None)
        self.description = kwargs.pop('description', '')
        self.values = kwargs.pop('values', [])
        self.filter = kwargs.pop('filter', '.*')
        self.filter_action = kwargs.pop('filter_action', 'None')
        self.check_action = kwargs.pop('check_action', 'None')
        self.action = kwargs.pop('action', None)

        self.set_extra_attributes_from_keyword_args(**kwargs)

        if self.value is None:
            self.value = self.default_value

        self.save_path = kwargs.pop('save_path', '')

        self.get_file_information_from_url()

    def filter_name(self, text):
        """Use the filter action to filter out invalid text"""
        if text and hasattr(self.filter_action, text):
            action = getattr(self.filter_action, text)
            return action(text)
        return text or ''

    def get_file_information_from_url(self):
        """Extract the file information from the setting url"""
        if hasattr(self, 'url'):
            self.file_name = self.url.split('/')[-1]
            self.full_file_path = utils.path_join(self.save_path, self.file_name)
            self.file_ext = os.path.splitext(self.file_name)[1]
            if self.file_ext == '.zip':
                self.extract_class = zipfile.ZipFile
                self.extract_args = ()
            elif self.file_ext == '.gz':
                self.extract_class = tarfile.TarFile.open
                self.extract_args = ('r:gz',)

    def save_file_path(self, version, location=None, sdk_build=False):
        """Get the save file path based on the version"""
        if location:
            self.save_path = location
        else:
            self.save_path = location or config.download_path()


        self.get_file_information_from_url()

        if self.full_file_path:

            path = self.full_file_path.format(version)

            if sdk_build:
                path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

            return path

        return ''

    def set_extra_attributes_from_keyword_args(self, **kwargs):
        for undefined_key, undefined_value in kwargs.items():
            setattr(self, undefined_key, undefined_value)

    def extract(self, ex_path, version, location=None, sdk_build=False):
        if os.path.exists(ex_path):
            utils.rmtree(ex_path, ignore_errors=True)

        path = location or self.save_file_path(version,
                                               sdk_build=sdk_build)

        file = self.extract_class(path,
                                  *self.extract_args)
        # currently, python's extracting mechanism for zipfile doesn't
        # copy file permissions, resulting in a binary that
        # that doesn't work. Copied from a patch here:
        # http://bugs.python.org/file34873/issue15795_cleaned.patch
        if path.endswith('.zip'):
            members = file.namelist()
            for zipinfo in members:
                minfo = file.getinfo(zipinfo)
                target = file.extract(zipinfo, ex_path)
                mode = minfo.external_attr >> 16 & 0x1FF
                os.chmod(target, mode)
        else:
            file.extractall(ex_path)

        if path.endswith('.tar.gz'):
            dir_name = utils.path_join(ex_path, os.path.basename(path).replace('.tar.gz', ''))
        else:
            dir_name = utils.path_join(ex_path, os.path.basename(path).replace('.zip', ''))

        if os.path.exists(dir_name):
            for p in os.listdir(dir_name):
                abs_file = utils.path_join(dir_name, p)
                utils.move(abs_file, ex_path)
            utils.rmtree(dir_name, ignore_errors=True)

    def __repr__(self):
        url = ''
        if hasattr(self, 'url'):
            url = self.url
        return (
            'Setting: (name={}, '
            'display_name={}, '
            'value={}, required={}, '
            'type={}, url={})'
        ).format(self.name,
                 self.display_name,
                 self.value,
                 self.required,
                 self.type,
                 url)

class CompleterLineEdit(QtWidgets.QLineEdit):

    def __init__(self, tag_dict, *args):
        QtWidgets.QLineEdit.__init__(self, *args)

        self.pref = ''
        self.tag_dict = tag_dict

    def text_changed(self, text):
        all_text = str(text)
        text = all_text[:self.cursorPosition()]
        prefix = re.split(r'(?<=\))(.*)(?=%\()', text)[-1].strip()
        self.pref = prefix
        if prefix.strip() != prefix:
            self.pref = ''

    def complete_text(self, text):
        cursor_pos = self.cursorPosition()
        before_text = str(self.text())[:cursor_pos]
        after_text = str(self.text())[cursor_pos:]
        prefix_len = len(re.split(r'(?<=\))(.*)(?=%\()', before_text)[-1].strip())
        tag_text = self.tag_dict.get(text)

        if tag_text is None:
            tag_text = text

        new_text = '{}{}{}'.format(before_text[:cursor_pos - prefix_len],
                                   tag_text,
                                   after_text)
        self.setText(new_text)
        self.setCursorPosition(len(new_text))

class TagsCompleter(QtWidgets.QCompleter):

    def __init__(self, parent, all_tags):
        self.keys = sorted(all_tags.keys())
        self.vals = sorted([val for val in all_tags.values()])
        self.tags = list(sorted(self.vals+self.keys))
        QtWidgets.QCompleter.__init__(self, self.tags, parent)
        self.editor = parent

    def update(self, text):
        obj = self.editor
        completion_prefix = obj.pref
        model = QtWidgets.QStringListModel(self.tags, self)
        self.setModel(model)

        self.setCompletionPrefix(completion_prefix)
        if completion_prefix.strip() != '':
            self.complete()
