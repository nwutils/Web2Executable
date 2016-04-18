from utils import log, open_folder_in_explorer

import os
import re
import glob
import sys
import codecs
import platform
import requests
import validators

from PySide import QtGui, QtCore
from PySide.QtGui import QApplication, QHBoxLayout, QVBoxLayout
from PySide.QtNetwork import QHttp
from PySide.QtCore import QUrl, QFile, QIODevice, QCoreApplication

from pycns import pngs_from_icns
from command_line import CommandBase, logger, get_file
from command_line import __version__ as __gui_version__

from utils import get_data_path, get_data_file_path
import utils

COMMAND_LINE = False

MAX_RECENT = 10

def url_exists(path):
    if validators.url(path):
        return True
    return False

class ExistingProjectDialog(QtGui.QDialog):
    def __init__(self, recent_projects, directory_callback, parent=None):
        super(ExistingProjectDialog, self).__init__(parent)
        self.setWindowTitle('Open Project Folder')
        self.setWindowIcon(QtGui.QIcon(get_file('files/images/icon.png')))
        self.setMinimumWidth(500)

        group_box = QtGui.QGroupBox('Existing Projects')
        gbox_layout = QtGui.QVBoxLayout()
        self.project_list = QtGui.QListWidget()

        gbox_layout.addWidget(self.project_list)
        group_box.setLayout(gbox_layout)

        self.callback = directory_callback

        self.projects = recent_projects

        for i in range(len(recent_projects)):
            project = recent_projects[i]
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

        directory = QtGui.QFileDialog.getExistingDirectory(self, 'Find Project Directory',
                self.parent().project_dir() or self.parent().last_project_dir)

        if directory:
            self.callback(directory)
            self.close()

    def open_clicked(self):
        pos = self.project_list.currentRow()
        self.callback(self.projects[pos])
        self.close()

    def project_clicked(self, item):
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


class MainWindow(QtGui.QMainWindow, CommandBase):

    def update_nw_versions(self, button):
        self.get_versions_in_background()

    def load_recent_projects(self):
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

    def load_last_project_path(self):
        proj_path = ''
        proj_file = get_data_file_path('files/last_project_path.txt')
        if os.path.exists(proj_file):
            with codecs.open(proj_file, encoding='utf-8') as f:
                proj_path = f.read().strip()

        if not proj_path:
            proj_path = QtCore.QDir.currentPath()

        return proj_path

    def save_project_path(self, path):
        proj_file = get_data_file_path('files/last_project_path.txt')
        with codecs.open(proj_file, 'w+', encoding='utf-8') as f:
            f.write(path)

    def save_recent_project(self, proj):
        recent_file_path = get_data_file_path('files/recent_files.txt')
        max_length = MAX_RECENT
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

    def update_recent_files(self):
        previous_files = self.load_recent_projects()
        self.recent_separator.setVisible(len(previous_files) > 0)
        for i in range(len(previous_files)):
            text = u'{} - {}'.format(i+1, os.path.basename(previous_files[i]))
            action = self.recent_file_actions[i]
            action.setText(text)
            action.setData(previous_files[i])
            action.setVisible(True)

    def __init__(self, width, height, app, parent=None):
        super(MainWindow, self).__init__(parent)
        CommandBase.__init__(self)

        recent_projects = self.load_recent_projects()

        self.existing_dialog = ExistingProjectDialog(recent_projects, self.load_project, parent=self)

        drect = QtGui.QApplication.desktop().availableGeometry(self)
        center = drect.center()
        self.move(center.x() - self.width() * 0.5, center.y() - self.height()*0.5)

        self.icon_style = 'width:48px;height:48px;background-color:white;border-radius:5px;border:1px solid rgb(50,50,50);'

        self.last_project_dir = self.load_last_project_path()

        status_bar = QtGui.QStatusBar()
        self.setStatusBar(status_bar)

        self.project_path = ''
        self.project_menu = self.menuBar().addMenu('File')
        browse_action = QtGui.QAction('Open Project', self.project_menu,
                                      shortcut=QtGui.QKeySequence.Open,
                                      statusTip='Open an existing or new project.',
                                      triggered=self.browse_dir)
        self.project_menu.addAction(browse_action)
        self.project_menu.addSeparator()

        self.recent_file_actions = []

        for i in range(MAX_RECENT):
            if i == 9:
                key = 0
            else:
                key = i+1
            action = QtGui.QAction(self, visible=False, triggered=self.open_recent_file,
                                   shortcut=QtGui.QKeySequence('Ctrl+{}'.format(key)))
            self.recent_file_actions.append(action)
            self.project_menu.addAction(action)

        self.recent_separator = self.project_menu.addSeparator()

        self.update_recent_files()

        exit_action = QtGui.QAction('Exit', self.project_menu)
        exit_action.triggered.connect(QtGui.qApp.closeAllWindows)
        self.project_menu.addAction(exit_action)

        self.logger = logger

        self.gui_app = app
        self.desktop_width = app.desktop().screenGeometry().width()
        self.desktop_height = app.desktop().screenGeometry().height()

        self.options_enabled = False
        self.output_package_json = True
        self.setWindowIcon(QtGui.QIcon(get_file('files/images/icon.png')))
        self.update_json = False

        self.setup_nw_versions()

        self.thread = None
        self.original_packagejson = {}

        self.resize(width, height)

        self.extract_error = None

        self.create_application_layout()

        self.option_settings_enabled(False)

        self.setWindowTitle(u"Web2Executable {}".format(__gui_version__))
        self.update_nw_versions(None)

    def open_recent_file(self):
        action = self.sender()
        if action:
            self.load_project(action.data())

    def setup_nw_versions(self):
        nw_version = self.get_setting('nw_version')
        try:
            f = codecs.open(get_data_file_path('files/nw-versions.txt'), encoding='utf-8')
            for line in f:
                nw_version.values.append(line.strip())
            f.close()
        except IOError:
            nw_version.values.append(nw_version.default_value)

    def create_application_layout(self):
        self.main_layout = QtGui.QVBoxLayout()
        self.tab_widget = QtGui.QTabWidget()
        self.main_layout.setContentsMargins(10, 5, 10, 5)

        self.create_layout_widgets()

        self.addWidgets_to_main_layout()

        w = QtGui.QWidget()
        w.setLayout(self.main_layout)

        self.setCentralWidget(w)

    def create_layout_widgets(self):
        self.download_bar_widget = self.create_download_bar()
        self.app_settings_widget = self.create_application_settings()
        self.comp_settings_widget = self.create_compression_settings()
        self.win_settings_widget = self.create_window_settings()
        self.ex_settings_widget = self.create_export_settings()
        self.dl_settings_widget = self.create_download_settings()
        self.directory_chooser_widget = self.create_directory_choose()

    def addWidgets_to_main_layout(self):
        self.warning_settings_icon = QtGui.QIcon(get_file('files/images/warning.png'))
        self.app_settings_icon = QtGui.QIcon(get_file('files/images/app_settings.png'))
        self.win_settings_icon = QtGui.QIcon(get_file('files/images/window_settings.png'))
        self.ex_settings_icon = QtGui.QIcon(get_file('files/images/export_settings.png'))
        self.comp_settings_icon = QtGui.QIcon(get_file('files/images/compress_settings.png'))
        self.download_settings_icon = QtGui.QIcon(get_file('files/images/download_settings.png'))

        self.tab_icons = [self.app_settings_icon,
                          self.win_settings_icon,
                          self.ex_settings_icon,
                          self.comp_settings_icon,
                          self.download_settings_icon]

        self.main_layout.addWidget(self.directory_chooser_widget)
        self.tab_widget.addTab(self.app_settings_widget,
                               self.app_settings_icon,
                               'App Settings')
        self.tab_widget.addTab(self.win_settings_widget,
                               self.win_settings_icon,
                               'Window Settings')
        self.tab_widget.addTab(self.ex_settings_widget,
                               self.ex_settings_icon, 'Export Settings')
        self.tab_widget.addTab(self.comp_settings_widget,
                               self.comp_settings_icon,
                               'Compression Settings')
        self.tab_widget.addTab(self.dl_settings_widget,
                               self.download_settings_icon,
                               'Download Settings')

        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.addLayout(self.download_bar_widget)

    def option_settings_enabled(self, is_enabled):
        self.ex_button.setEnabled(is_enabled)
        self.app_settings_widget.setEnabled(is_enabled)
        self.win_settings_widget.setEnabled(is_enabled)
        self.ex_settings_widget.setEnabled(is_enabled)
        self.comp_settings_widget.setEnabled(is_enabled)
        self.dl_settings_widget.setEnabled(is_enabled)
        self.options_enabled = is_enabled

    def export(self, export_button, cancel_button):
        self.get_files_to_download()
        self.try_to_download_files()

    def open_export(self, open_export_button):
        open_folder_in_explorer(self.output_dir())

    def try_to_download_files(self):
        if self.files_to_download:
            self.progress_bar.setVisible(True)
            self.cancel_button.setEnabled(True)
            self.disable_ui_while_working()

            self.download_file_with_error_handling()
        else:
            # This shouldn't happen since we disable the UI if there are no
            # options selected
            # But in the weird event that this does happen, we are prepared!
            QtGui.QMessageBox.information(self,
                                          'Export Options Empty!',
                                          ('Please choose one of '
                                           'the export options!'))

    def selected_version(self):
        return self.get_setting('nw_version').value

    def enable_ui_after_error(self):
        self.enable_ui()
        self.progress_text = ''
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)

    def show_error(self, exception):
        QtGui.QMessageBox.information(self, 'Error!', exception)

    def disable_ui_while_working(self):
        self.option_settings_enabled(False)
        self.directory_chooser_widget.setEnabled(False)

    def enable_ui(self):
        self.option_settings_enabled(True)
        self.directory_chooser_widget.setEnabled(True)

    def get_tab_index_for_setting_name(self, name):
        options_dict = {'app_settings': 0,
                        'webkit_settings': 0,
                        'window_settings': 1,
                        'export_settings': 2,
                        'web2exe_settings': 2,
                        'compression': 3,
                        'download_settings': 4}
        for setting_group_name, setting_group in self._setting_items:
            if name in setting_group:
                return options_dict.get(setting_group_name, None)

    def required_settings_filled(self, ignore_options=False):
        if not self.options_enabled and not ignore_options:
            return False

        red_border = 'QLineEdit{border:3px solid rgba(238, 68, 83, 200); border-radius:5px;}'

        settings_valid = True
        for sgroup in self.settings['setting_groups']+[self.settings['web2exe_settings']]:
            for sname, setting in sgroup.items():
                if setting.type in set(['file', 'folder']) and os.path.isabs(setting.value):
                    setting_path = setting.value
                else:
                    setting_path = utils.path_join(self.project_dir(),
                                                   setting.value)

                if setting.required and not setting.value:
                    settings_valid = False
                    widget = self.find_child_by_name(setting.name)
                    if widget is not None:
                        widget.setStyleSheet(red_border)
                        widget.setToolTip('This setting is required.')
                        tab = self.get_tab_index_for_setting_name(setting.name)
                        self.tab_widget.setTabIcon(tab, self.warning_settings_icon)

                if (setting.type == 'file' and
                        setting.value):
                    setting_path_invalid = not os.path.exists(setting_path)
                    setting_url_invalid = not url_exists(setting.value)
                    if setting_path_invalid and setting_url_invalid:
                        log(setting.value, "does not exist")
                        settings_valid = False
                        widget = self.find_child_by_name(setting.name)
                        if widget is not None:
                            widget.setStyleSheet(red_border)
                            widget.setToolTip(u'The file or url "{}" does not exist.'.format(setting.value))
                            tab = self.get_tab_index_for_setting_name(setting.name)
                            self.tab_widget.setTabIcon(tab, self.warning_settings_icon)

                if (setting.type == 'folder' and
                    setting.value and
                        not os.path.exists(setting_path)):
                    settings_valid = False
                    widget = self.find_child_by_name(setting.name)
                    if widget is not None:
                        widget.setStyleSheet(red_border)
                        widget.setToolTip(u'The folder "{}" does not exist'.format(setting_path))
                        tab = self.get_tab_index_for_setting_name(setting.name)
                        self.tab_widget.setTabIcon(tab, self.warning_settings_icon)
                if settings_valid:
                    widget = self.find_child_by_name(setting.name)
                    if widget is not None:
                        widget.setStyleSheet('')
                        widget.setToolTip('')
                        tab = self.get_tab_index_for_setting_name(setting.name)
                        self.tab_widget.setTabIcon(tab, self.tab_icons[tab])

        export_chosen = False
        for setting_name, setting in self.settings['export_settings'].items():
            if setting.value:
                export_chosen = True

        if not settings_valid:
            return export_chosen and settings_valid

        for setting_name, setting in self.settings['export_settings'].items():
            if not export_chosen:
                widget = self.find_child_by_name(setting.name)
                if widget is not None:
                    widget.setStyleSheet('QCheckBox{border:3px solid rgba(238, 68, 83, 200); border-radius:5px;}')
                    widget.setToolTip('At least one of these options should be selected.')
                    tab = self.get_tab_index_for_setting_name(setting.name)
                    self.tab_widget.setTabIcon(tab, self.warning_settings_icon)
            else:
                widget = self.find_child_by_name(setting.name)
                if widget is not None:
                    widget.setStyleSheet('')
                    widget.setToolTip('')
                    tab = self.get_tab_index_for_setting_name(setting.name)
                    self.tab_widget.setTabIcon(tab, self.tab_icons[tab])

        return export_chosen and settings_valid

    def project_dir(self):
        return self.project_path
        if hasattr(self, 'input_line'):
            return self.input_line.text()
        return ''

    def output_dir(self):
        if hasattr(self, 'output_line'):
            if os.path.isabs(self.output_line.text()):
                return self.output_line.text()
            else:
                return utils.path_join(self.project_dir(), self.output_line.text())
        return ''

    def create_download_bar(self):
        hlayout = QtGui.QHBoxLayout()

        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(5, 5, 5, 5)
        vlayout.setSpacing(5)
        hlayout.setSpacing(5)
        hlayout.setContentsMargins(5, 5, 5, 5)

        progress_label = QtGui.QLabel('')
        progress_bar = QtGui.QProgressBar()
        progress_bar.setVisible(False)
        progress_bar.setContentsMargins(5, 5, 5, 5)

        vlayout.addWidget(progress_label)
        vlayout.addWidget(progress_bar)
        vlayout.addWidget(QtGui.QLabel(''))

        ex_button = QtGui.QPushButton('Export')
        ex_button.setEnabled(False)

        cancel_button = QtGui.QPushButton('Cancel Download')
        cancel_button.setEnabled(False)

        open_export_button = QtGui.QPushButton()
        open_export_button.setEnabled(False)
        open_export_button.setIcon(QtGui.QIcon(get_file('files/images/folder_open.png')))
        open_export_button.setToolTip('Open Export Folder')
        open_export_button.setStatusTip('Open Export Folder')
        open_export_button.setMaximumWidth(30)
        open_export_button.setMaximumHeight(30)

        ex_button.clicked.connect(self.call_with_object('export', ex_button, cancel_button))
        cancel_button.clicked.connect(self.cancel_download)
        open_export_button.clicked.connect(self.call_with_object('open_export', open_export_button))

        button_box = QtGui.QDialogButtonBox()
        button_box.addButton(open_export_button, QtGui.QDialogButtonBox.NoRole)
        button_box.addButton(cancel_button, QtGui.QDialogButtonBox.RejectRole)
        button_box.addButton(ex_button, QtGui.QDialogButtonBox.AcceptRole)

        hlayout.addLayout(vlayout)
        hlayout.addWidget(button_box)

        self.progress_label = progress_label
        self.progress_bar = progress_bar
        self.cancel_button = cancel_button
        self.open_export_button = open_export_button

        http = QHttp(self)
        http.requestFinished.connect(self.http_request_finished)
        http.dataReadProgress.connect(self.update_progress_bar)
        http.responseHeaderReceived.connect(self.read_response_header)
        self.http = http
        self.ex_button = ex_button

        return hlayout

    def read_response_header(self, response_header):
        # Check for genuine error conditions.
        if response_header.statusCode() not in (200, 300, 301, 302, 303, 307):
            self.show_error(u'Download failed: {}.'.format(response_header.reasonPhrase()))
            self.http_request_aborted = True
            self.http.abort()
            self.enable_ui_after_error()

    def http_request_finished(self, request_id, error):
        if request_id != self.http_get_id:
            return

        if self.http_request_aborted:
            if self.out_file is not None:
                self.out_file.close()
                self.out_file.remove()
                self.out_file = None
            return

        self.out_file.close()
        self.http.abort()

        if error:
            self.out_file.remove()
            self.show_error(u'Download failed: {}.'.format(self.http.errorString()))
            self.enable_ui_after_error()
        else:
            self.continue_downloading_or_extract()

    def continue_downloading_or_extract(self):
        if self.files_to_download:
            self.progress_bar.setVisible(True)
            self.cancel_button.setEnabled(True)
            self.disable_ui_while_working()

            self.download_file_with_error_handling()
        else:
            self.progress_text = 'Done.'
            self.cancel_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.extract_files_in_background()

    @property
    def progress_text(self):
        return self.progress_label.text()

    @progress_text.setter
    def progress_text(self, value):
        self.progress_label.setText(value)

    def run_in_background(self, method_name, callback):
        self.thread = BackgroundThread(self, method_name)
        self.thread.finished.connect(callback)
        self.thread.start()

    def get_versions_in_background(self):
        self.ex_button.setEnabled(False)
        self.run_in_background('get_versions', self.done_getting_versions)

    def done_getting_versions(self):
        self.ex_button.setEnabled(self.required_settings_filled())
        self.progress_text = 'Done retrieving versions.'

        nw_version = self.get_setting('nw_version')
        combo = self.find_child_by_name(nw_version.name)

        combo.clear()
        combo.addItems(nw_version.values)

    def make_output_files_in_background(self):
        self.ex_button.setEnabled(False)
        self.run_in_background('make_output_dirs', self.done_making_files)

    def run_custom_script(self):
        script = self.get_setting('custom_script').value
        self.run_script(script)

    def script_done(self):
        self.ex_button.setEnabled(self.required_settings_filled())
        self.enable_ui()
        self.progress_text = 'Done!'

    def done_making_files(self):
        self.ex_button.setEnabled(self.required_settings_filled())
        self.progress_text = 'Done Exporting.'
        self.delete_files()

        if self.output_err:
            self.show_error(self.output_err)
            self.enable_ui_after_error()
        else:
            self.progress_text = 'Running custom script...'
            self.ex_button.setEnabled(False)
            self.run_in_background('run_custom_script', self.script_done)

    def extract_files_in_background(self):
        self.progress_text = 'Extracting.'
        self.ex_button.setEnabled(False)

        self.run_in_background('extract_files', self.done_extracting)

    def done_extracting(self):
        self.ex_button.setEnabled(self.required_settings_filled())
        if self.extract_error:
            self.progress_text = 'Error extracting.'
            self.show_error('There were one or more errors with your '
                            'zip/tar files. They were deleted. Please '
                            'try to export again.')

            self.enable_ui_after_error()

        else:
            self.progress_text = 'Done extracting.'
            self.make_output_files_in_background()

    def cancel_download(self):
        self.progress_text = 'Download cancelled.'
        self.cancel_button.setEnabled(False)
        self.http_request_aborted = True
        self.http.abort()
        self.enable_ui()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

    def update_progress_bar(self, bytes_read, total_bytes):
        if self.http_request_aborted:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)
            return
        self.progress_bar.setMaximum(total_bytes)
        self.progress_bar.setValue(bytes_read)

    def download_file(self, path, setting):
        version_file = self.settings['base_url'].format(self.selected_version())

        sdk_build_setting = self.get_setting('sdk_build')
        sdk_build = sdk_build_setting.value

        location = self.get_setting('download_dir').value

        versions = re.findall('v(\d+)\.(\d+)\.(\d+)', path)[0]

        minor = int(versions[1])
        if minor >= 12:
            path = path.replace('node-webkit', 'nwjs')

        if minor >= 13 and sdk_build:
            path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

        self.progress_text = u'Downloading {}'.format(path.replace(version_file, ''))

        url = QUrl(path)
        file_name = setting.save_file_path(self.selected_version(), location, sdk_build)

        archive_exists = QFile.exists(file_name)

        forced = self.get_setting('force_download').value

        if archive_exists and not forced:
            self.continue_downloading_or_extract()
            return

        self.out_file = QFile(file_name)
        if not self.out_file.open(QIODevice.WriteOnly):
            error = self.out_file.error().name
            self.show_error(u'Unable to save the file {}: {}.'.format(file_name,
                                                                     error))
            self.out_file = None
            self.enable_ui()
            return

        mode = QHttp.ConnectionModeHttp
        port = url.port()
        if port == -1:
            port = 0
        self.http.setHost(url.host(), mode, port)
        self.http_request_aborted = False

        path = QUrl.toPercentEncoding(url.path(), "!$&'()*+,;=:@/")
        if path:
            path = str(path)
        else:
            path = u'/'

        # Download the file.
        self.http_get_id = self.http.get(path, self.out_file)

    def create_icon_box(self, name, text):
        style = 'width:48px;height:48px;background-color:white;border-radius:5px;border:1px solid rgb(50,50,50);'
        icon_label = QtGui.QLabel()
        icon_label.setStyleSheet(style)
        icon_label.setMaximumWidth(48)
        icon_label.setMinimumWidth(48)
        icon_label.setMaximumHeight(48)
        icon_label.setMinimumHeight(48)

        setattr(self, name, icon_label)

        icon_text = QtGui.QLabel(text)
        icon_text.setStyleSheet('font-size:10px;')
        icon_text.setAlignment(QtCore.Qt.AlignCenter)
        vbox = QVBoxLayout()
        vbox.setAlignment(QtCore.Qt.AlignCenter)
        vbox.addWidget(icon_label)
        vbox.addWidget(icon_text)
        vbox.setContentsMargins(0, 0, 0, 0)

        w = QtGui.QWidget()
        w.setLayout(vbox)
        w.setMaximumWidth(70)
        return w

    def create_directory_choose(self):
        group_box = QtGui.QGroupBox('An awesome web project called:')

        title_hbox = QHBoxLayout()
        title_hbox.setContentsMargins(10, 10, 10, 10)

        win_icon = self.create_icon_box('window_icon', 'Window Icon')
        exe_icon = self.create_icon_box('exe_icon', 'Exe Icon')
        mac_icon = self.create_icon_box('mac_icon', 'Mac Icon')

        self.title_label = QtGui.QLabel('TBD')
        self.title_label.setStyleSheet('font-size:20px; font-weight:bold;')
        title_hbox.addWidget(self.title_label)
        title_hbox.addWidget(QtGui.QLabel())
        title_hbox.addWidget(win_icon)
        title_hbox.addWidget(exe_icon)
        title_hbox.addWidget(mac_icon)

        vlayout = QtGui.QVBoxLayout()

        vlayout.setSpacing(5)
        vlayout.setContentsMargins(10, 5, 10, 5)

        vlayout.addLayout(title_hbox)

        group_box.setLayout(vlayout)

        return group_box

    def set_window_icon(self):
        icon_setting = self.get_setting('icon')
        mac_icon_setting = self.get_setting('mac_icon')
        exe_icon_setting = self.get_setting('exe_icon')
        self.set_icon(icon_setting.value, self.window_icon)
        if not mac_icon_setting.value:
            self.set_icon(icon_setting.value, self.mac_icon)
        if not exe_icon_setting.value:
            self.set_icon(icon_setting.value, self.exe_icon)

    def set_exe_icon(self):
        icon_setting = self.get_setting('exe_icon')
        self.set_icon(icon_setting.value, self.exe_icon)

    def set_mac_icon(self):
        icon_setting = self.get_setting('mac_icon')
        self.set_icon(icon_setting.value, self.mac_icon)

    def set_icon(self, icon_path, icon):
        if icon_path:
            icon_path = utils.path_join(self.project_dir(), icon_path)
            if os.path.exists(icon_path):
                if icon_path.endswith('.icns'):
                    pngs = pngs_from_icns(icon_path)
                    if pngs:
                        image = QtGui.QImage.fromData(QtCore.QByteArray(pngs[-1].data), 'PNG')
                    else:
                        return
                else:
                    image = QtGui.QImage(icon_path)
                if image.width() >= image.height():
                    image = image.scaledToWidth(48,
                                        QtCore.Qt.SmoothTransformation)
                else:
                    image = image.scaledToHeight(48,
                                        QtCore.Qt.SmoothTransformation)
                icon.setPixmap(QtGui.QPixmap.fromImage(image))
                icon.setStyleSheet('')
            else:
                icon.setPixmap(None)
                icon.setStyleSheet(self.icon_style)
        else:
            icon.setPixmap(None)
            icon.setStyleSheet(self.icon_style)


    def call_with_object(self, name, obj, *args, **kwargs):
        """Allows arguments to be passed to click events"""
        def call(*cargs, **ckwargs):
            if hasattr(self, name):
                func = getattr(self, name)
                kwargs.update(ckwargs)
                func(obj, *(args+cargs), **kwargs)
        return call

    def find_child_by_name(self, name):
        return self.findChild(QtCore.QObject, name)

    def find_all_children(self, names):
        children = []
        for child in self.find_children(QtCore.QObject):
            if child.object_name() in names:
                children.append(child)

        return children

    def project_name(self):
        return self.find_child_by_name('app_name').text()

    def browse_dir(self):
        directory = QtGui.QFileDialog.getExistingDirectory(self, 'Find Project Directory',
                self.project_dir() or self.last_project_dir)

        if directory:
            self.load_project(directory)

    def load_project(self, directory):
        self.update_json = False
        self.project_path = directory
        self.save_recent_project(directory)
        self.save_project_path(directory)
        self.update_recent_files()
        self.reset_settings()

        proj_name = os.path.basename(directory)
        self.title_label.setText(proj_name)

        setting_input = self.find_child_by_name('main')
        files = (glob.glob(utils.path_join(directory, 'index.html')) +
                 glob.glob(utils.path_join(directory, 'index.php')) +
                 glob.glob(utils.path_join(directory, 'index.htm')))
        if not setting_input.text():
            if files:
                setting_input.setText(files[0].replace(self.project_dir() + os.path.sep, ''))

        app_name_input = self.find_child_by_name('app_name')
        name_input = self.find_child_by_name('name')
        name_setting = self.get_setting('name')
        title_input = self.find_child_by_name('title')

        if not name_input.text():
            name_input.setText(name_setting.filter_name(proj_name))

        if not app_name_input.text():
            app_name_input.setText(proj_name)

        if not title_input.text():
            title_input.setText(proj_name)

        self.load_package_json(utils.get_data_file_path('files/global.json'))
        self.load_package_json()

        default_dir = 'output'
        export_dir_setting = self.get_setting('export_dir')
        default_dir = export_dir_setting.value or default_dir
        self.output_line.setText(default_dir)

        script_setting = self.get_setting('custom_script')
        self.script_line.setText(script_setting.value)

        self.set_window_icon()
        self.open_export_button.setEnabled(True)
        self.update_json = True

    def browse_out_dir(self):
        self.update_json = False
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Choose Output Directory",
                                                             (self.output_line.text() or
                                                              self.project_dir() or
                                                              self.last_project_dir))
        if directory:
            self.update_json = True
            self.output_line.setText(directory)

    def get_file(self, obj, text_obj, setting, *args, **kwargs):
        file_path, _ = QtGui.QFileDialog.getOpenFileName(self, 'Choose File',
                                                         (setting.last_value or
                                                          self.project_dir() or
                                                          QtCore.QDir.currentPath()),
                                                         setting.file_types)
        if file_path:
            file_path = os.path.abspath(file_path) # fixes an issue with windows paths
            file_path = file_path.replace(self.project_dir()+os.path.sep, '')
            text_obj.setText(file_path)
            setting.last_value = file_path

    def get_file_reg(self, obj, text_obj, setting, file_types, *args, **kwargs):
        file_path, _ = QtGui.QFileDialog.getOpenFileName(self, 'Choose File',
                                                         (setting.last_value or
                                                          self.project_dir() or
                                                          QtCore.QDir.currentPath()),
                                                          file_types)
        if file_path:
            file_path = os.path.abspath(file_path) # fixes an issue with windows paths
            file_path = file_path.replace(self.project_dir()+os.path.sep, '')
            text_obj.setText(file_path)
            setting.last_value = file_path

    def get_folder(self, obj, text_obj, setting, *args, **kwargs):
        folder = QtGui.QFileDialog.getExistingDirectory(self, 'Choose Folder',
                                                        (setting.last_value or
                                                         QtCore.QDir.currentPath()))
        if folder:
            folder = folder.replace(self.project_dir()+os.path.sep, '')
            text_obj.setText(folder)
            setting.last_value = folder

    def create_application_settings(self):
        group_box = QtGui.QWidget()
        vlayout = self.create_layout(self.settings['order']['application_setting_order'], cols=3)

        group_box.setLayout(vlayout)
        return group_box

    def create_compression_settings(self):
        group_box = QtGui.QWidget()
        vlayout = self.create_layout(self.settings['order']['compression_setting_order'], cols=1)
        warning_label = QtGui.QLabel('Note: When using compression (greater than 0) it will decrease the executable size,\nbut will increase the startup time when running it.')
        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(vlayout)
        vbox.addWidget(warning_label)
        group_box.setLayout(vbox)
        return group_box

    def create_setting(self, name):
        setting = self.get_setting(name)
        if setting.type == 'string':
            return self.create_text_input_setting(name)
        elif setting.type == 'strings':
            return self.create_text_input_setting(name)
        elif setting.type == 'file':
            return self.create_text_input_with_file_setting(name)
        elif setting.type == 'folder':
            return self.create_text_input_with_folder_setting(name)
        elif setting.type == 'check':
            return self.create_check_setting(name)
        elif setting.type == 'list':
            return self.create_list_setting(name)
        elif setting.type == 'range':
            return self.create_range_setting(name)

    def create_window_settings(self):
        group_box = QtGui.QWidget()
        vlayout = self.create_layout(self.settings['order']['window_setting_order'], cols=3)

        group_box.setLayout(vlayout)
        return group_box

    def create_export_settings(self):
        group_box = QtGui.QWidget()
        vlayout = self.create_layout(self.settings['order']['export_setting_order'], cols=4)

        output_layout = QtGui.QHBoxLayout()

        output_label = QtGui.QLabel('Output Directory:')
        output_label.setMinimumWidth(150)
        self.output_line = QtGui.QLineEdit()
        self.output_line.textChanged.connect(self.call_with_object('setting_changed',
                                                                   self.output_line,
                                                                   self.get_setting('export_dir')))
        self.output_line.textChanged.connect(self.project_path_changed)
        self.output_line.setStatusTip('The output directory relative to the project directory.')
        output_button = QtGui.QPushButton('...')
        output_button.clicked.connect(self.browse_out_dir)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(output_button)

        script_layout = QtGui.QHBoxLayout()

        script_label = QtGui.QLabel('Execute Script:')
        script_label.setMinimumWidth(150)

        self.script_line = QtGui.QLineEdit()

        script_setting = self.get_setting('custom_script')
        self.script_line.setObjectName(script_setting.name)

        self.script_line.textChanged.connect(self.call_with_object('setting_changed',
                                                                   self.script_line,
                                                                   script_setting))
        self.script_line.setStatusTip('The script to execute after a project was successfully exported.')
        script_button = QtGui.QPushButton('...')

        file_types = ['*.py']

        if platform.system() == 'Windows':
            file_types.append('*.bat')
        else:
            file_types.append('*.bash')

        script_button.clicked.connect(self.call_with_object('get_file_reg', script_button,
                                                            self.script_line, script_setting,
                                                            ' '.join(file_types)))
        script_layout.addWidget(script_label)
        script_layout.addWidget(self.script_line)
        script_layout.addWidget(script_button)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(vlayout)
        vbox.addLayout(output_layout)
        vbox.addLayout(script_layout)

        group_box.setLayout(vbox)
        return group_box

    def create_download_settings(self):
        group_box = QtGui.QWidget()
        vlayout = self.create_layout(self.settings['order']['download_setting_order'], cols=1)

        group_box.setLayout(vlayout)
        return group_box

    def create_layout(self, settings, cols=3):
        glayout = QtGui.QGridLayout()
        glayout.setContentsMargins(10, 15, 10, 5)
        glayout.setAlignment(QtCore.Qt.AlignTop)
        glayout.setSpacing(10)
        glayout.setHorizontalSpacing(20)
        col = 0
        row = 0

        for setting_name in settings:
            setting = self.get_setting(setting_name)
            if col >= cols*2:
                row += 1
                col = 0
            display_name = setting.display_name+':'
            if setting.required:
                display_name += '*'
            setting_label = QtGui.QLabel(display_name)
            setting_label.setToolTip(setting.description)
            setting_label.setStatusTip(setting.description)
            glayout.addWidget(setting_label, row, col)
            glayout.addLayout(self.create_setting(setting_name),
                              row, col+1)
            col += 2

        return glayout

    def create_text_input_setting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        text = QtGui.QLineEdit()
        text.setValidator(Validator(setting.filter, setting.filter_action))
        text.setObjectName(setting.name)

        text.textChanged.connect(self.call_with_object('setting_changed',
                                                       text, setting))
        if setting.value:
            text.setText(setting.value)
        text.setStatusTip(setting.description)
        text.setToolTip(setting.description)

        hlayout.addWidget(text)

        return hlayout

    def create_text_input_with_file_setting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        text = QtGui.QLineEdit()
        text.setObjectName(setting.name)

        button = QtGui.QPushButton('...')
        button.setMaximumWidth(30)
        button.setMaximumHeight(26)

        button.clicked.connect(self.call_with_object('get_file', button,
                                                     text, setting))

        if setting.value:
            text.setText(setting.value)
        text.setStatusTip(setting.description)
        text.setToolTip(setting.description)

        text.textChanged.connect(self.call_with_object('setting_changed',
                                                        text, setting))

        hlayout.addWidget(text)
        hlayout.addWidget(button)

        return hlayout

    def create_text_input_with_folder_setting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        text = QtGui.QLineEdit()
        text.setObjectName(setting.name)

        button = QtGui.QPushButton('...')
        button.setMaximumWidth(30)
        button.setMaximumHeight(26)

        button.clicked.connect(self.call_with_object('get_folder', button,
                                                   text, setting))

        if setting.value:
            text.setText(setting.value)
        text.setStatusTip(setting.description)
        text.setToolTip(setting.description)

        text.textChanged.connect(self.call_with_object('setting_changed',
                                                     text, setting))

        hlayout.addWidget(text)
        hlayout.addWidget(button)

        return hlayout

    def reset_settings(self):
        for sgroup in self.settings['setting_groups']:
            for setting in sgroup.values():
                widget = self.find_child_by_name(setting.name)
                if widget is None:
                    continue

                if (setting.type == 'string' or
                    setting.type == 'file' or
                        setting.type == 'folder'):
                    old_val = ''

                    if setting.default_value is not None:
                        old_val = setting.default_value

                    setting.value = old_val.replace('\\', '\\\\')
                    widget.setText(old_val)
                elif setting.type == 'strings':
                    old_val = []
                    if setting.default_value is not None:
                        old_val = setting.default_value
                    setting.value = [v.replace('\\', '\\\\') for v in old_val]
                    widget.setText(','.join(setting.value))

                elif setting.type == 'check':
                    old_val = False

                    if setting.default_value is not None:
                        old_val = setting.default_value

                    setting.value = old_val
                    widget.setChecked(old_val)

                elif setting.type == 'range':
                    old_val = 0
                    if setting.default_value is not None:
                        old_val = setting.default_value
                    setting.value = old_val
                    widget.setValue(old_val)

    def set_kiosk_emulation_options(self, is_checked):
        if is_checked:
            width_field = self.find_child_by_name('width')
            width_field.setText(self.desktop_width)

            height_field = self.find_child_by_name('height')
            height_field.setText(self.desktop_height)

            toolbar_field = self.find_child_by_name('toolbar')
            toolbar_field.setChecked(not is_checked)

            frame_field = self.find_child_by_name('frame')
            frame_field.setChecked(not is_checked)

            show_field = self.find_child_by_name('show')
            show_field.setChecked(is_checked)

            kiosk_field = self.find_child_by_name('kiosk')
            kiosk_field.setChecked(not is_checked)

            fullscreen_field = self.find_child_by_name('fullscreen')
            fullscreen_field.setChecked(not is_checked)

            always_on_top_field = self.find_child_by_name('always-on-top')
            always_on_top_field.setChecked(is_checked)

            resizable_field = self.find_child_by_name('resizable')
            resizable_field.setChecked(not is_checked)

    def refresh_export(self):
        versions = self.get_version_tuple()
        major_ver = versions[0]
        minor_ver = versions[1]

        mac = self.find_child_by_name('mac-x32')
        if (major_ver > 0 or minor_ver >= 13):
            if mac:
                mac.setEnabled(False)
        else:
            if mac:
                mac.setEnabled(True)

    def setting_changed(self, obj, setting, *args, **kwargs):
        if (setting.type == 'string' or
            setting.type == 'file' or
                setting.type == 'folder'):
            setting.value = args[0]
        elif setting.type == 'strings':
            setting.value = args[0].split(',')
        elif setting.type == 'check':
            setting.value = obj.isChecked()
            check_action = setting.check_action
            if hasattr(self, check_action):
                getattr(self, check_action)(obj.isChecked())
        elif setting.type == 'list':
            setting.value = obj.currentText()
        elif setting.type == 'range':
            setting.value = obj.value()

        if setting.action is not None:
            action = getattr(self, setting.action, None)
            if callable(action):
                action()

        if self.update_json:
            json_file = utils.path_join(self.project_dir(), 'package.json')

            global_json = utils.get_data_file_path('files/global.json')

            with codecs.open(json_file, 'w+', encoding='utf-8') as f:
                f.write(self.generate_json())

            with codecs.open(global_json, 'w+', encoding='utf-8') as f:
                f.write(self.generate_json(global_json=True))

        self.ex_button.setEnabled(self.required_settings_filled())

    def project_path_changed(self, text):
        self.ex_button.setEnabled(self.required_settings_filled(True))

        dirs_filled_out = False
        if self.project_dir() and self.output_dir():
            if os.path.exists(self.project_dir()):
                dirs_filled_out = True

        self.option_settings_enabled(dirs_filled_out)

    def create_check_setting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        check = QtGui.QCheckBox()

        check.setObjectName(setting.name)

        check.clicked.connect(self.call_with_object('setting_changed',
                                                    check, setting))
        check.setChecked(setting.value)
        check.setStatusTip(setting.description)
        check.setToolTip(setting.description)

        hlayout.addWidget(check)

        return hlayout

    def create_list_setting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        button = None
        if setting.button:
            button = QtGui.QPushButton(setting.button)
            button.clicked.connect(lambda: setting.button_callback(button))
        combo = QtGui.QComboBox()

        combo.setObjectName(setting.name)

        combo.currentIndexChanged.connect(self.call_with_object('setting_changed',
                                                                  combo, setting))
        combo.editTextChanged.connect(self.call_with_object('setting_changed',
                                                              combo, setting))

        combo.setStatusTip(setting.description)
        combo.setToolTip(setting.description)

        for val in setting.values:
            combo.addItem(val)

        default_index = combo.findText(setting.default_value)
        if default_index != -1:
            combo.setCurrentIndex(default_index)

        hlayout.addWidget(QtGui.QLabel())
        hlayout.addWidget(combo)
        if button:
            hlayout.addWidget(button)

        return hlayout

    def create_range_setting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        button = None
        if setting.button:
            button = QtGui.QPushButton(setting.button)
            button.clicked.connect(lambda: setting.button_callback(button))

        slider = QtGui.QSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setRange(setting.min, setting.max)
        slider.valueChanged.connect(self.call_with_object('setting_changed',
                                                          slider, setting))

        slider.setObjectName(setting.name)
        slider.setValue(setting.default_value)
        slider.setStatusTip(setting.description)
        slider.setToolTip(setting.description)

        range_label = QtGui.QLabel(str(setting.default_value))
        range_label.setMaximumWidth(30)

        slider.valueChanged.connect(self.call_with_object('_update_range_label',
                                                          range_label))

        w = QtGui.QWidget()
        whlayout = QtGui.QHBoxLayout()
        whlayout.addWidget(slider)
        whlayout.addWidget(range_label)
        w.setLayout(whlayout)

        hlayout.addWidget(w)

        return hlayout

    def _update_range_label(self, label, value):
        label.setText(str(value))

    def load_package_json(self, json_path=None):
        setting_list = super(MainWindow, self).load_package_json(json_path)
        for setting in setting_list:
            setting_field = self.find_child_by_name(setting.name)
            if setting_field:
                if (setting.type == 'file' or
                    setting.type == 'string' or
                        setting.type == 'folder'):
                    val_str = self.convert_val_to_str(setting.value)
                    setting_field.setText(setting.filter_name(val_str))
                if setting.type == 'strings':
                    vals = [self.convert_val_to_str(v) for v in setting.value]
                    setting_field.setText(','.join(vals))
                if setting.type == 'check':
                    setting_field.setChecked(setting.value)
                if setting.type == 'list':
                    val_str = self.convert_val_to_str(setting.value)
                    index = setting_field.findText(val_str)
                    if index != -1:
                        setting_field.setCurrentIndex(index)
                if setting.type == 'range':
                    setting_field.setValue(int(setting.value))
        self.ex_button.setEnabled(self.required_settings_filled())

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.existing_dialog.show()
        self.existing_dialog.raise_()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    QCoreApplication.setApplicationName("Web2Executable")
    QCoreApplication.setApplicationVersion(__gui_version__)
    QCoreApplication.setOrganizationName("SimplyPixelated")
    QCoreApplication.setOrganizationDomain("simplypixelated.com")

    frame = MainWindow(900, 500, app)
    frame.show_and_raise()

    sys.exit(app.exec_())
