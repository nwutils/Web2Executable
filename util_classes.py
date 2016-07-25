import os
import re
import zipfile
import tarfile

import config
import utils

from PySide import QtGui, QtCore

class ExistingProjectDialog(QtGui.QDialog):
    def __init__(self, recent_projects, directory_callback, parent=None):
        super(ExistingProjectDialog, self).__init__(parent)
        self.setWindowTitle('Open Project Folder')
        self.setWindowIcon(QtGui.QIcon(config.get_file('files/images/icon.png')))
        self.setMinimumWidth(500)

        group_box = QtGui.QGroupBox('Existing Projects')
        gbox_layout = QtGui.QVBoxLayout()
        self.project_list = QtGui.QListWidget()

        gbox_layout.addWidget(self.project_list)
        group_box.setLayout(gbox_layout)

        self.callback = directory_callback

        self.projects = recent_projects

        for project in recent_projects:
            text = u'{} - {}'.format(os.path.basename(project), project)
            self.project_list.addItem(text)

        self.project_list.itemClicked.connect(self.project_clicked)

        self.cancel = QtGui.QPushButton('Cancel')
        self.open = QtGui.QPushButton('Open Selected')
        self.browse = QtGui.QPushButton('Browse...')

        self.open.setEnabled(False)
        self.open.clicked.connect(self.open_clicked)

        self.browse.clicked.connect(self.browse_clicked)

        buttons = QtGui.QWidget()

        button_layout = QtGui.QHBoxLayout()
        button_layout.addWidget(self.cancel)
        button_layout.addWidget(QtGui.QWidget())
        button_layout.addWidget(self.browse)
        button_layout.addWidget(self.open)

        buttons.setLayout(button_layout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(group_box)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.cancel.clicked.connect(self.cancelled)

    def browse_clicked(self):

        default = self.parent().project_dir() or self.parent().last_project_dir

        directory = QtGui.QFileDialog.getExistingDirectory(self, 'Find Project Directory',
                                                           default)

        if directory:
            self.callback(directory)
            self.close()

    def open_clicked(self):
        pos = self.project_list.currentRow()
        self.callback(self.projects[pos])
        self.close()

    def project_clicked(self, _):
        self.open.setEnabled(True)

    def cancelled(self):
        self.close()

class Validator(QtGui.QRegExpValidator):
    def __init__(self, regex, action, parent=None):
        self.exp = regex
        self.action = str
        if hasattr(str, action):
            self.action = getattr(str, action)
        reg = QtCore.QRegExp(regex)
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
        self.description = kwargs.pop('description', u'')
        self.values = kwargs.pop('values', [])
        self.filter = kwargs.pop('filter', '.*')
        self.filter_action = kwargs.pop('filter_action', 'None')
        self.check_action = kwargs.pop('check_action', 'None')
        self.action = kwargs.pop('action', None)

        self.set_extra_attributes_from_keyword_args(**kwargs)

        if self.value is None:
            self.value = self.default_value

        self.save_path = kwargs.pop('save_path', u'')

        self.get_file_information_from_url()

    def filter_name(self, text):
        """Use the filter action to filter out invalid text"""
        if hasattr(self.filter_action, text):
            action = getattr(self.filter_action, text)
            return action(text)
        return text

    def get_file_information_from_url(self):
        """Extract the file information from the setting url"""
        if hasattr(self, 'url'):
            self.file_name = self.url.split(u'/')[-1]
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
            self.save_path = self.save_path or config.DEFAULT_DOWNLOAD_PATH


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

    def extract(self, ex_path, version, sdk_build=False):
        if os.path.exists(ex_path):
            utils.rmtree(ex_path, ignore_errors=True)

        path = self.save_file_path(version, sdk_build=sdk_build)

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
            u'Setting: (name={}, '
            u'display_name={}, '
            u'value={}, required={}, '
            u'type={}, url={})'
        ).format(self.name,
                 self.display_name,
                 self.value,
                 self.required,
                 self.type,
                 url)
