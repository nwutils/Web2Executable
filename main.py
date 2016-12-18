# -*- coding: utf-8 -*-
"""Web2Executable

An application that creates cross platform executables from HTML and Nodejs
web applications powered by NW.js.

This is the main module that handles all the GUI interaction and generation.
The GUI is automatically generated from the config file located in
`files/settings.cfg`.

Since the GUI is automatically generated, the settings.cfg contains many
configuration options for each element. Also, this class is set up so that
any time a user interacts with an element in the GUI, the underlying data
is modified and can be accessed via
``self.get_setting("setting_name_from_settings_cfg").value``.

Run Example:
    All that is needed to run the following after running instructions in
    `SETUP.md`.

        $ python3.4 main.py

"""
import os
import glob
import sys
import logging
import platform

import config

import utils
from utils import log, open_folder_in_explorer

from config import get_file
from config import __version__ as __gui_version__

from util_classes import ExistingProjectDialog
from util_classes import BackgroundThread, Validator
from util_classes import CompleterLineEdit, TagsCompleter
from util_classes import TreeBrowser

from PySide import QtGui, QtCore
from PySide.QtGui import (QApplication, QHBoxLayout, QVBoxLayout)
from PySide.QtNetwork import QHttp
from PySide.QtCore import Qt, QUrl, QFile, QIODevice, QCoreApplication

from image_utils.pycns import pngs_from_icns

from command_line import CommandBase

class MainWindow(QtGui.QMainWindow, CommandBase):
    """The main window of Web2Executable."""

    def update_nw_versions(self, button=None):
        """Update NW version list in the background."""
        self.get_versions_in_background()

    def update_recent_files(self):
        """Update the recent files list in the menu bar."""
        previous_files = utils.load_recent_projects()
        self.recent_separator.setVisible(len(previous_files) > 0)
        for i, prev_file in enumerate(previous_files):
            text = '{} - {}'.format(i+1, os.path.basename(prev_file))
            action = self.recent_file_actions[i]
            action.setText(text)
            action.setData(prev_file)
            action.setVisible(True)

    def __init__(self, width, height, app, parent=None):
        super(MainWindow, self).__init__(parent)
        CommandBase.__init__(self, quiet=True)

        self.script_line = None
        self.output_line = None
        self.output_name_line = None

        self.download_bar_widget = None
        self.app_settings_widget = None
        self.comp_settings_widget = None
        self.win_settings_widget = None
        self.ex_settings_widget = None
        self.dl_settings_widget = None
        self.project_info_widget = None

        self.warning_settings_icon = None
        self.app_settings_icon = None
        self.win_settings_icon = None
        self.ex_settings_icon = None
        self.comp_settings_icon = None
        self.download_settings_icon = None

        self.tab_icons = None

        self.progress_label = None
        self.progress_bar = None
        self.cancel_button = None
        self.open_export_button = None

        self.http = None
        self.ex_button = None

        self.extract_error = None

        self.options_enabled = False
        self.output_package_json = True
        self.update_json = False
        self.original_packagejson = {}

        self.thread = None
        self.readonly = False

        self.recent_file_actions = []
        self.project_path = ''

        self.tab_index_dict = {
            'app_settings': 0,
            'webkit_settings': 0,
            'window_settings': 1,
            'export_settings': 2,
            'web2exe_settings': 2,
            'compression': 3,
            'download_settings': 4
        }

        recent_projects = utils.load_recent_projects()

        self.existing_dialog = ExistingProjectDialog(recent_projects,
                                                     self.load_project,
                                                     parent=self)

        # initialize application to middle of screen
        drect = QtGui.QApplication.desktop().availableGeometry(self)
        center = drect.center()
        self.move(center.x() - self.width()*0.5,
                  center.y() - self.height()*0.5)

        self.icon_style = ('width:48px;height:48px;background-color:white;'
                           'border-radius:5px;border:1px solid rgb(50,50,50);')

        self.last_project_dir = utils.load_last_project_path()

        status_bar = QtGui.QStatusBar()
        self.setStatusBar(status_bar)

        self.setup_project_menu()

        self.logger = logging.getLogger(__name__)

        self.gui_app = app
        self.desktop_width = app.desktop().screenGeometry().width()
        self.desktop_height = app.desktop().screenGeometry().height()

        self.setWindowIcon(QtGui.QIcon(get_file(config.ICON_PATH)))

        self.setup_nw_versions()

        self.resize(width, height)

        self.create_application_layout()

        self.option_settings_enabled(False)

        self.setWindowTitle(u"Web2Executable {}".format(__gui_version__))
        self.update_nw_versions(None)

    def setup_project_menu(self):
        """Set up the project menu bar with actions."""
        self.project_menu = self.menuBar().addMenu('File')
        self.edit_menu = self.menuBar().addMenu('Edit')

        browse_action = QtGui.QAction('Open Project', self.project_menu,
                                      shortcut=QtGui.QKeySequence.Open,
                                      statusTip='Open an existing or new project.',
                                      triggered=self.browse_dir)

        toggle_readonly_action = QtGui.QAction('Toggle Readonly',
                                               self.edit_menu,
                                               shortcut='Ctrl+R',
                                               statusTip='Toggle Readonly',
                                               triggered=self.toggle_readonly)

        self.edit_menu.addAction(toggle_readonly_action)
        self.project_menu.addAction(browse_action)
        self.project_menu.addSeparator()

        # Display last 10 projects
        for i in range(config.MAX_RECENT):
            if i == 9:
                # Display 0 last
                key = 0
            else:
                key = i+1
            action = QtGui.QAction(self, visible=False,
                                   triggered=self.open_recent_file,
                                   shortcut=QtGui.QKeySequence('Ctrl+{}'.format(key)))
            self.recent_file_actions.append(action)
            self.project_menu.addAction(action)

        self.recent_separator = self.project_menu.addSeparator()

        self.update_recent_files()

        exit_action = QtGui.QAction('Exit', self.project_menu)
        exit_action.triggered.connect(QtGui.qApp.closeAllWindows)
        self.project_menu.addAction(exit_action)

    def open_recent_file(self):
        """Loads a project based on the most recent file selected."""
        action = self.sender()
        if action:
            self.load_project(action.data())

    def create_application_layout(self):
        """Create all widgets and set the central widget."""
        self.main_layout = QtGui.QVBoxLayout()
        self.tab_widget = QtGui.QTabWidget()
        self.main_layout.setContentsMargins(10, 5, 10, 5)

        self.create_layout_widgets()

        self.add_widgets_to_main_layout()

        w = QtGui.QWidget()
        w.setLayout(self.main_layout)

        self.setCentralWidget(w)

    def create_layout_widgets(self):
        """Create individual layouts that are displayed in tabs."""
        self.download_bar_widget = self.create_download_bar()
        self.app_settings_widget = self.create_application_settings()
        self.comp_settings_widget = self.create_compression_settings()
        self.win_settings_widget = self.create_window_settings()
        self.ex_settings_widget = self.create_export_settings()
        self.dl_settings_widget = self.create_download_settings()
        self.project_info_widget = self.create_project_info()

    def add_widgets_to_main_layout(self):
        """Add all of the widgets and icons to the main layout."""
        self.warning_settings_icon = QtGui.QIcon(get_file(config.WARNING_ICON))
        self.app_settings_icon = QtGui.QIcon(get_file(config.APP_SETTINGS_ICON))
        self.win_settings_icon = QtGui.QIcon(get_file(config.WINDOW_SETTINGS_ICON))
        self.ex_settings_icon = QtGui.QIcon(get_file(config.EXPORT_SETTINGS_ICON))
        self.comp_settings_icon = QtGui.QIcon(get_file(config.COMPRESS_SETTINGS_ICON))
        self.download_settings_icon = QtGui.QIcon(get_file(config.DOWNLOAD_SETTINGS_ICON))

        self.tab_icons = [self.app_settings_icon,
                          self.win_settings_icon,
                          self.ex_settings_icon,
                          self.comp_settings_icon,
                          self.download_settings_icon]

        self.main_layout.addWidget(self.project_info_widget)
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

    def toggle_readonly(self):
        self.readonly = not self.readonly

        self.app_settings_widget.setEnabled(not self.readonly)
        self.win_settings_widget.setEnabled(not self.readonly)

    def option_settings_enabled(self, is_enabled):
        """
        Set all settings widgets to either be enabled or disabled.

        This is used to enable/disable the entire GUI except for loading
        new projects so the user can't interact with it.
        """
        self.ex_button.setEnabled(is_enabled)
        self.app_settings_widget.setEnabled(is_enabled)
        self.win_settings_widget.setEnabled(is_enabled)
        if self.readonly:
            self.app_settings_widget.setEnabled(False)
            self.win_settings_widget.setEnabled(False)
        self.ex_settings_widget.setEnabled(is_enabled)
        self.comp_settings_widget.setEnabled(is_enabled)
        self.dl_settings_widget.setEnabled(is_enabled)
        self.options_enabled = is_enabled

    def export(self):
        """Start an export after the user clicks 'Export'."""
        self.get_files_to_download()
        self.try_to_download_files()

    def open_export(self):
        """Open the export folder in the file explorer."""
        open_folder_in_explorer(self.output_dir())

    def try_to_download_files(self):
        """
        If there are files that need to be downloaded, this attempts to
        retrieve them. If any errors occur, display them, cancel the
        download and reenable the UI.
        """
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
        """Get the currently selected version."""
        return self.get_setting('nw_version').value

    def enable_ui_after_error(self):
        """
        This will reenable the UI and hide the progress bar in the event
        of an error.
        """
        self.enable_ui()
        self.progress_text = ''
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)

    def show_error(self, exception):
        """
        Show an error with QMessageBox. Does not work when not
        in the UI thread (ie: when downloading files)!

        Args:
            exception (Exception): an error that has occurred
        """
        QtGui.QMessageBox.information(self, 'Error!', exception)

    def disable_ui_while_working(self):
        self.option_settings_enabled(False)
        self.project_info_widget.setEnabled(False)

    def enable_ui(self):
        self.option_settings_enabled(True)
        self.project_info_widget.setEnabled(True)

    def get_tab_index_for_setting_name(self, name):
        """Return the tab index based on the name of the setting."""
        for setting_group_name, setting_group in self._setting_items:
            if name in setting_group:
                return self.tab_index_dict.get(setting_group_name, None)

    def required_settings_filled(self, ignore_options=False):
        """
        Determines if there are any issues in the currently filled out
        settings. If there are issues, error fields are highlighted.
        """

        if not self.options_enabled and not ignore_options:
            return False

        settings_valid = self.settings_valid()

        export_chosen = False
        for setting in self.settings['export_settings'].values():
            if setting.value:
                export_chosen = True

        if not settings_valid:
            return export_chosen and settings_valid

        # check export settings to make sure at least one is checked
        for setting in self.settings['export_settings'].values():
            if not export_chosen:
                widget = self.find_child_by_name(setting.name)
                if widget is not None:
                    widget.setStyleSheet('QCheckBox{border:3px solid '
                                         'rgba(238, 68, 83, 200); '
                                         'border-radius:5px;}')
                    widget.setToolTip('At least one of these '
                                      'options should be selected.')
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

    def settings_valid(self):
        """Determines if settings that are filled out in the GUI are valid.

        Displays a red border on any setting that is invalid and a warning
        icon on the corresponding tab.
        """

        red_border = ('QLineEdit{border:3px solid rgba(238, 68, 83, 200); '
                      'border-radius:5px;}')

        settings_valid = True
        for sgroup in self.settings['setting_groups']+[self.settings['web2exe_settings']]:
            for _, setting in sgroup.items():
                if setting.value:
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

                if setting.type == 'int' and setting.value != '':
                    try:
                        int(setting.value or '0')
                    except ValueError:
                        settings_valid = False
                        widget = self.find_child_by_name(setting.name)
                        if widget is not None:
                            widget.setStyleSheet(red_border)
                            tip = 'The value {} must be an integer.'.format(setting.value)
                            widget.setToolTip(tip)
                            tab = self.get_tab_index_for_setting_name(setting.name)
                            self.tab_widget.setTabIcon(tab, self.warning_settings_icon)

                if (setting.type == 'file' and
                        setting.value):
                    setting_path_invalid = not os.path.exists(setting_path)
                    setting_url_invalid = not utils.url_exists(setting.value)
                    if setting_path_invalid and setting_url_invalid:
                        log(setting.value, "does not exist")
                        settings_valid = False
                        widget = self.find_child_by_name(setting.name)
                        if widget is not None:
                            widget.setStyleSheet(red_border)
                            tip = 'The file or url "{}" does not exist.'.format(setting.value)
                            widget.setToolTip(tip)
                            tab = self.get_tab_index_for_setting_name(setting.name)
                            self.tab_widget.setTabIcon(tab, self.warning_settings_icon)

                if (setting.type == 'folder' and
                        setting.value and
                        not os.path.exists(setting_path)):
                    settings_valid = False
                    widget = self.find_child_by_name(setting.name)
                    if widget is not None:
                        widget.setStyleSheet(red_border)
                        widget.setToolTip('The folder "{}" does not exist'.format(setting_path))
                        tab = self.get_tab_index_for_setting_name(setting.name)
                        self.tab_widget.setTabIcon(tab, self.warning_settings_icon)
                if settings_valid:
                    widget = self.find_child_by_name(setting.name)
                    if widget is not None:
                        widget.setStyleSheet('')
                        widget.setToolTip('')
                        tab = self.get_tab_index_for_setting_name(setting.name)
                        self.tab_widget.setTabIcon(tab, self.tab_icons[tab])

        return settings_valid

    def project_dir(self):
        return self.project_path

    def output_dir(self):
        """Get the project output directory."""
        if hasattr(self, 'output_line'):
            if os.path.isabs(self.output_line.text()):
                return self.output_line.text()
            else:
                return utils.path_join(self.project_dir(),
                                       self.output_line.text())
        return ''

    def create_download_bar(self):
        """
        Create the bottom bar of the GUI with the progress bar and
        export button.
        """
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
        open_export_button.setIcon(QtGui.QIcon(get_file(config.FOLDER_OPEN_ICON)))
        open_export_button.setToolTip('Open Export Folder')
        open_export_button.setStatusTip('Open Export Folder')
        open_export_button.setMaximumWidth(30)
        open_export_button.setMaximumHeight(30)

        ex_button.clicked.connect(self.export)
        cancel_button.clicked.connect(self.cancel_download)
        open_export_button.clicked.connect(self.open_export)

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
        """
        Read the response header of a download and show an error if an
        invalid response code is shown.
        """
        # Check for genuine error conditions.
        if response_header.statusCode() not in (200, 300, 301, 302, 303, 307):
            self.show_error('Download failed: {}.'.format(response_header.reasonPhrase()))
            self.http_request_aborted = True
            self.http.abort()
            self.enable_ui_after_error()

    def http_request_finished(self, request_id, error):
        """
        After the request is finished, keep downloading files if they exist.
        If all files are done downloading, start extracting them.
        """
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
            self.show_error('Download failed: {}.'.format(self.http.errorString()))
            self.enable_ui_after_error()
        else:
            self.continue_downloading_or_extract()

    def continue_downloading_or_extract(self):
        """Keep downloading files if they exist, otherwise extract."""
        if self.files_to_download:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.cancel_button.setEnabled(True)
            self.disable_ui_while_working()

            self.download_file_with_error_handling()
        else:
            self.progress_text = 'Done.'
            self.cancel_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)
            self.extract_files_in_background()

    @property
    def progress_text(self):
        """Lets the user see progress on the GUI as tasks are performed."""
        return self.progress_label.text()

    @progress_text.setter
    def progress_text(self, value):
        self.progress_label.setText(value)

    def run_in_background(self, method_name, callback):
        """
        Run any method in this class in the background, then
        call the callback.

        Args:
            method_name (string): the name of a method on self
            callback (function): the function to run in the background
        """
        self.thread = BackgroundThread(self, method_name)
        self.thread.finished.connect(callback)
        self.thread.start()

    def get_versions_in_background(self):
        self.ex_button.setEnabled(False)
        self.run_in_background('get_versions', self.done_getting_versions)

    def done_getting_versions(self):
        """
        After getting versions, enable the UI and update the
        versions combobox.
        """
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
        """Run the custom script setting"""
        script = self.get_setting('custom_script').value
        self.run_script(script)

    def script_done(self):
        self.ex_button.setEnabled(self.required_settings_filled())
        self.enable_ui()
        self.progress_text = 'Done!'

    def done_making_files(self):
        """
        After creating files and directories, show an error if it exists,
        otherwise run the user's custom script.
        """
        self.ex_button.setEnabled(self.required_settings_filled())
        self.progress_text = 'Done Exporting.'
        self.delete_files()

        if self.output_err:
            self.show_error(self.output_err)
            self.enable_ui_after_error()
            self.output_err = ''
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
        """Cancel downloading if the user presses the cancel button."""
        self.progress_text = 'Download cancelled.'
        self.cancel_button.setEnabled(False)
        self.http_request_aborted = True
        self.http.abort()
        self.enable_ui()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

    def update_progress_bar(self, bytes_read, total_bytes):
        """Show progress of download on the progress bar."""
        if self.http_request_aborted:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)
            return
        self.progress_bar.setMaximum(total_bytes)
        self.progress_bar.setValue(bytes_read)

    def download_file(self, path, setting):
        """Download an NW archive file.

        Args:
            path (string): the URL path of the file
            setting (Setting): The file setting to download
        """
        version_file = self.settings['base_url'].format(self.selected_version())

        sdk_build_setting = self.get_setting('sdk_build')
        sdk_build = sdk_build_setting.value

        location = self.get_setting('download_dir').value or config.download_path()

        if sdk_build:
            # Switch the download URL if an sdk build is selected
            path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

        self.progress_text = 'Downloading {}'.format(path.replace(version_file,
                                                                  ''))

        url = QUrl(path)
        file_name = setting.save_file_path(self.selected_version(),
                                           location, sdk_build)

        archive_exists = QFile.exists(file_name)
        forced = self.get_setting('force_download').value

        # Don't download if file already exists
        if archive_exists and not forced:
            self.continue_downloading_or_extract()
            return

        self.out_file = QFile(file_name)
        # If the file could not be opened, show the error and abort!
        if not self.out_file.open(QIODevice.WriteOnly):
            error = self.out_file.error().name
            self.show_error('Unable to save the file {}: {}.'.format(file_name,
                                                                     error))
            self.out_file = None
            self.enable_ui()
            return

        # Download in HTTP mode
        mode = QHttp.ConnectionModeHttp
        port = url.port()

        if port == -1:
            port = 0

        # Set up the download host
        self.http.setHost(url.host(), mode, port)
        self.http_request_aborted = False

        # Normalize path
        path = QUrl.toPercentEncoding(url.path(), "!$&'()*+,;=:@/")
        if path:
            path = str(path)
        else:
            path = '/'

        # Download the file.
        self.http_get_id = self.http.get(path, self.out_file)

    def create_icon_box(self, name, text):
        style = ('width:48px;height:48px;background-color:white;'
                 'border-radius:5px;border:1px solid rgb(50,50,50);')
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

    def create_project_info(self):
        """Create the GroupBox that shows the user's project name and icons."""
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
        """
        Set the icon to the icon widget specified.

        Args:
            icon_path (string): the path to the new icon
            icon (QWidget): the widget to set the icon for
        """
        if icon_path:
            icon_path = utils.path_join(self.project_dir(), icon_path)
            if os.path.exists(icon_path):
                if icon_path.endswith('.icns'):
                    pngs = pngs_from_icns(icon_path)
                    if pngs:
                        bdata = QtCore.QByteArray(pngs[-1].data)
                        image = QtGui.QImage.fromData(bdata, 'PNG')
                    else:
                        return
                else:
                    image = QtGui.QImage(icon_path)
                trans = QtCore.Qt.SmoothTransformation
                if image.width() >= image.height():
                    image = image.scaledToWidth(48, trans)
                else:
                    image = image.scaledToHeight(48, trans)
                icon.setPixmap(QtGui.QPixmap.fromImage(image))
                icon.setStyleSheet('')
                return

        icon.setPixmap(None)
        icon.setStyleSheet(self.icon_style)

    def call_with_object(self, name, obj, *args, **kwargs):
        """
        Allows arguments to be passed to click events so the calling object
        is not lost.
        """
        def call(*cargs, **ckwargs):
            if hasattr(self, name):
                func = getattr(self, name)
                kwargs.update(ckwargs)
                func(obj, *(args+cargs), **kwargs)
        return call

    def find_child_by_name(self, name):
        """Finds a GUI element by setting name"""
        return self.findChild(QtCore.QObject, name)

    def find_all_children(self, names):
        """
        Find all children referenced by the names list.

        Args:
            names (list): a list of strings that are setting names
        """
        children = []
        for child in self.find_children(QtCore.QObject):
            if child.object_name() in names:
                children.append(child)

        return children

    def project_name(self):
        """Get the current GUI project name field."""
        return self.find_child_by_name('app_name').text()

    def browse_dir(self):
        """
        Open a directory browsing window for the user to choose a
        directory.
        """
        dir_func = QtGui.QFileDialog.getExistingDirectory
        directory = dir_func(self, 'Find Project Directory',
                             self.project_dir() or self.last_project_dir)

        if directory:
            self.load_project(directory)

    def load_project(self, directory, readonly=False):
        """Load a new project from a directory."""
        self.update_json = False
        self.readonly = readonly
        self.project_path = directory

        utils.save_recent_project(directory)
        utils.save_project_path(directory)

        self.update_recent_files()
        self.reset_settings()

        proj_name = os.path.basename(directory)
        self.title_label.setText(proj_name)

        self.init_main_field(directory)

        self.init_input_fields(proj_name)

        # Load the global json and then overwrite the settings with user
        # chosen values
        self.load_package_json()
        self.load_package_json(utils.get_data_file_path(config.GLOBAL_JSON_FILE))
        self.load_package_json(utils.path_join(self.project_dir(),
                                               config.WEB2EXE_JSON_FILE))

        default_dir = 'output'
        export_dir_setting = self.get_setting('export_dir')
        default_dir = export_dir_setting.value or default_dir
        self.output_line.setText(default_dir)

        script_setting = self.get_setting('custom_script')
        self.script_line.setText(script_setting.value)

        # Setup output name setting
        output_name_setting = self.get_setting('output_pattern')
        self.output_name_line.setText(output_name_setting.value)

        self.output_name_line.textChanged.connect(self.output_name_line.text_changed)
        self.output_name_line.textChanged.connect(self.completer.update)

        self.set_window_icon()
        self.open_export_button.setEnabled(True)

        blacklist_setting = self.get_setting('blacklist')

        output_blacklist = os.path.basename(self.output_dir())

        self.tree_browser.init(directory,
                               blacklist=(blacklist_setting.value.split('\n') +
                                          ['*'+output_blacklist+'*']))

        self.update_json = True

    def init_main_field(self, directory):
        """Initialize main html or php file."""
        setting_input = self.find_child_by_name('main')

        if not setting_input.text():
            files = (glob.glob(utils.path_join(directory, 'index.html')) +
                     glob.glob(utils.path_join(directory, 'index.php')) +
                     glob.glob(utils.path_join(directory, 'index.htm')))
            if files:
                # get the first valid file and use that
                setting_input.setText(files[0].replace(self.project_dir() +
                                                            os.path.sep,
                                                       ''))

    def init_input_fields(self, proj_name):
        """Initialize input fields with project name."""
        app_name_input = self.find_child_by_name('app_name')
        name_input = self.find_child_by_name('name')
        name_setting = self.get_setting('name')
        title_input = self.find_child_by_name('title')
        id_input = self.find_child_by_name('id')

        if not name_input.text():
            name_input.setText(name_setting.filter_name(proj_name))

        if not app_name_input.text():
            app_name_input.setText(proj_name)

        if not title_input.text():
            title_input.setText(proj_name)

        if not id_input.text():
            id_input.setText(proj_name)

    def browse_out_dir(self):
        """Browse for an output directory by showing a dialog."""
        self.update_json = False
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Choose Output Directory",
                                                           (self.output_line.text() or
                                                            self.project_dir() or
                                                            self.last_project_dir))
        if directory:
            self.update_json = True
            self.output_line.setText(directory)

    def get_file(self, text_obj, setting):
        """
        Show a file browsing dialog for choosing a file.

        Args:
            text_obj (QTextField): the text field widget to store the
                                   selected file name in
            setting (Setting): the related setting object
        """
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

    def get_file_reg(self, text_obj, setting, file_types):
        """
        Open a file dialog with valid files specified with a regex.

        Args:
            text_obj (QTextField): the text field widget to store the
                                   selected file name in
            setting (Setting): the related setting object
            file_types (string): file types specified by a regex
                                 (eg. "*.py|*.html")
        """
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

    def get_folder(self, text_obj, setting):
        """
        Open a folder dialog to get a user chosen folder.

        Args:
            text_obj (QTextField): the text field widget to store the
                                   selected folder name in
            setting (Setting): the related setting object
        """

        folder = QtGui.QFileDialog.getExistingDirectory(self, 'Choose Folder',
                                                        (setting.last_value or
                                                         QtCore.QDir.currentPath()))
        if folder:
            folder = folder.replace(self.project_dir()+os.path.sep, '')
            text_obj.setText(folder)
            setting.last_value = folder

    def create_application_settings(self):
        group_box = QtGui.QWidget()
        app_setting = self.settings['order']['application_setting_order']
        vlayout = self.create_layout(app_setting, cols=3)

        group_box.setLayout(vlayout)
        return group_box

    def create_compression_settings(self):
        group_box = QtGui.QWidget()
        comp_setting = self.settings['order']['compression_setting_order']
        vlayout = self.create_layout(comp_setting, cols=1)
        warning_label = QtGui.QLabel('Note: When using compression (greater '
                                     'than 0) it will decrease the executable '
                                     'size,\nbut will increase the startup '
                                     'time when running it.')
        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(vlayout)
        vbox.addWidget(warning_label)
        group_box.setLayout(vbox)
        return group_box

    def create_setting(self, name):
        """
        Handle all of the dynamic setting creation logic based on the
        setting name.

        Args:
            name (string): the name of the setting to create
        """
        setting = self.get_setting(name)
        res = None

        if setting.type == 'string' or setting.type == 'int':
            res = self.create_text_input_setting(name)
        elif setting.type == 'strings':
            res = self.create_text_input_setting(name)
        elif setting.type == 'file':
            res = self.create_text_input_with_file_setting(name)
        elif setting.type == 'folder':
            res = self.create_text_input_with_folder_setting(name)
        elif setting.type == 'check':
            res = self.create_check_setting(name)
        elif setting.type == 'list':
            res = self.create_list_setting(name)
        elif setting.type == 'range':
            res = self.create_range_setting(name)

        return res

    def create_window_settings(self):
        group_box = QtGui.QWidget()
        win_setting_order = self.settings['order']['window_setting_order']
        vlayout = self.create_layout(win_setting_order, cols=3)

        group_box.setLayout(vlayout)
        return group_box

    def create_export_settings(self):
        group_box = QtGui.QWidget()

        ex_setting_order = self.settings['order']['export_setting_order']

        vlayout = self.create_layout(ex_setting_order, cols=1)
        vlayout.setContentsMargins(0, 10, 0, 0)

        output_name_layout = self.create_output_name_pattern_line()

        output_layout = self.create_output_directory_line()

        script_layout = self.create_script_layout()

        hlayout = QtGui.QHBoxLayout()

        platform_group = QtGui.QGroupBox('Platforms')
        platform_group.setContentsMargins(0, 10, 0, 0)
        playout = QtGui.QVBoxLayout()
        playout.addLayout(vlayout)
        platform_group.setLayout(playout)

        hlayout.addWidget(platform_group)

        tree_layout = self.create_blacklist_layout(hlayout)
        tree_layout.setContentsMargins(0, 10, 0, 0)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hlayout)
        vbox.addLayout(output_name_layout)
        vbox.addLayout(output_layout)
        vbox.addLayout(script_layout)

        group_box.setLayout(vbox)
        return group_box

    def create_blacklist_layout(self, blacklist_layout):

        self.tree_browser = TreeBrowser()
        self.tree_browser.setContentsMargins(0, 0, 0, 0)

        self.blacklist_text = QtGui.QPlainTextEdit()
        self.whitelist_text = QtGui.QPlainTextEdit()

        hlayout = QtGui.QHBoxLayout()

        blacklayout = QtGui.QVBoxLayout()
        whitelayout = QtGui.QHBoxLayout()

        blacklayout.addWidget(self.blacklist_text)
        whitelayout.addWidget(self.whitelist_text)

        whitelist_setting = self.get_setting('whitelist')
        blacklist_setting = self.get_setting('blacklist')

        self.blacklist_text.setStatusTip(blacklist_setting.description)
        self.whitelist_text.setStatusTip(whitelist_setting.description)

        self.blacklist_text.setObjectName(blacklist_setting.name)
        self.whitelist_text.setObjectName(whitelist_setting.name)

        blackgroup = QtGui.QGroupBox(blacklist_setting.display_name)
        whitegroup = QtGui.QGroupBox(whitelist_setting.display_name)

        blackgroup.setLayout(blacklayout)
        whitegroup.setLayout(whitelayout)

        blacklist_layout.addWidget(blackgroup)
        blacklist_layout.addWidget(whitegroup)
        blacklist_layout.addWidget(self.tree_browser)

        self.blacklist_text.textChanged.connect(
            self.call_with_object('setting_changed',
                                  self.blacklist_text,
                                  blacklist_setting)
        )

        self.whitelist_text.textChanged.connect(
            self.call_with_object('setting_changed',
                                  self.whitelist_text,
                                  whitelist_setting)
        )

        self.blacklist_text.textChanged.connect(
            self.call_with_object('blacklist_changed',
                                  self.blacklist_text,
                                  blacklist_setting)
        )

        self.whitelist_text.textChanged.connect(
            self.call_with_object('whitelist_changed',
                                  self.whitelist_text,
                                  whitelist_setting)
        )

        return blacklist_layout

    def blacklist_changed(self, text, blacklist_setting):
        new_val = text.toPlainText()
        output_blacklist = os.path.basename(self.output_dir())
        self.tree_browser.refresh(blacklist=(new_val.split('\n') +
                                            ['*'+output_blacklist+'*']))

    def whitelist_changed(self, text, whitelist_setting):
        new_val = text.toPlainText()
        self.tree_browser.refresh(whitelist=new_val.split('\n'))

    @property
    def used_project_files(self):
        return self.tree_browser.files

    @property
    def used_project_dirs(self):
        return self.tree_browser.dirs

    def create_output_name_pattern_line(self):
        output_name_layout = QtGui.QHBoxLayout()

        output_name_setting = self.get_setting('output_pattern')
        output_name_label = QtGui.QLabel(output_name_setting.display_name+':')
        output_name_label.setMinimumWidth(155)

        tag_dict = self.get_tag_dict()
        self.output_name_line = CompleterLineEdit(tag_dict)

        completer = TagsCompleter(self.output_name_line, tag_dict)
        completer.setCaseSensitivity(Qt.CaseInsensitive)

        completer.activated.connect(self.output_name_line.complete_text)
        self.completer = completer
        self.completer.setWidget(self.output_name_line)

        self.output_name_line.textChanged.connect(
            self.call_with_object('setting_changed',
                                  self.output_name_line,
                                  output_name_setting)
        )

        self.output_name_line.setStatusTip(output_name_setting.description)

        output_name_layout.addWidget(output_name_label)
        output_name_layout.addWidget(self.output_name_line)
        return output_name_layout

    def create_output_directory_line(self):
        output_layout = QtGui.QHBoxLayout()

        ex_dir_setting = self.get_setting('export_dir')
        output_label = QtGui.QLabel(ex_dir_setting.display_name+':')
        output_label.setMinimumWidth(155)
        self.output_line = QtGui.QLineEdit()

        self.output_line.textChanged.connect(
            self.call_with_object('setting_changed',
                                  self.output_line,
                                  ex_dir_setting)
        )

        self.output_line.textChanged.connect(self.project_path_changed)
        self.output_line.setStatusTip(ex_dir_setting.description)
        output_button = QtGui.QPushButton('...')
        output_button.clicked.connect(self.browse_out_dir)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(output_button)

        return output_layout

    def create_script_layout(self):
        script_layout = QtGui.QHBoxLayout()

        script_setting = self.get_setting('custom_script')
        script_label = QtGui.QLabel(script_setting.display_name+':')
        script_label.setMinimumWidth(155)

        self.script_line = QtGui.QLineEdit()

        self.script_line.setObjectName(script_setting.name)

        self.script_line.textChanged.connect(
            self.call_with_object('setting_changed',
                                  self.script_line,
                                  script_setting)
        )
        self.script_line.setStatusTip(script_setting.description)
        script_button = QtGui.QPushButton('...')

        file_types = ['*.py']

        if platform.system() == 'Windows':
            file_types.append('*.bat')
        else:
            file_types.append('*.bash')

        script_button.clicked.connect(
            self.call_with_object('get_file_reg',
                                  self.script_line,
                                  script_setting,
                                  ' '.join(file_types))
        )

        script_layout.addWidget(script_label)
        script_layout.addWidget(self.script_line)
        script_layout.addWidget(script_button)

        return script_layout

    def create_download_settings(self):
        group_box = QtGui.QWidget()
        dl_setting = self.settings['order']['download_setting_order']
        vlayout = self.create_layout(dl_setting, cols=1)

        group_box.setLayout(vlayout)
        return group_box

    def create_layout(self, settings, cols=3):
        """
        Create the generic layout for a group of settings.

        Args:
            settings (list): all settings to be part of the layout
            cols (int): number of columns to divide up the layout
        """

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
        """Create a generic text input with the setting name."""
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
        """
        Create a generic text input and file browse button with the
        setting name.
        """
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        text = QtGui.QLineEdit()
        text.setObjectName(setting.name)

        button = QtGui.QPushButton('...')
        button.setMaximumWidth(30)
        button.setMaximumHeight(26)

        button.clicked.connect(self.call_with_object('get_file',
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
        """
        Create a generic text input and folder browse button with the
        setting name.
        """
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        text = QtGui.QLineEdit()
        text.setObjectName(setting.name)

        button = QtGui.QPushButton('...')
        button.setMaximumWidth(30)
        button.setMaximumHeight(26)

        button.clicked.connect(self.call_with_object('get_folder',
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
        """Reset all of the settings to their defaults."""
        for sgroup in self.settings['setting_groups']:
            for setting in sgroup.values():
                widget = self.find_child_by_name(setting.name)
                if widget is None or setting.value is None:
                    continue

                if (setting.type == 'string' or
                        setting.type == 'file' or
                        setting.type == 'folder' or
                        setting.type == 'int'):
                    old_val = ''

                    if setting.default_value is not None:
                        old_val = setting.default_value

                    setting.value = old_val.replace('\\', '\\\\')
                    if hasattr(widget, 'setText'):
                        widget.setText(old_val)
                    elif hasattr(widget, 'setPlainText'):
                        widget.setPlainText(old_val)
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
        """Emulate kiosk mode on platforms that don't support it."""
        if is_checked:
            width_field = self.find_child_by_name('width')
            width_field.setText(str(self.desktop_width))

            height_field = self.find_child_by_name('height')
            height_field.setText(str(self.desktop_height))

            frame_field = self.find_child_by_name('frame')
            frame_field.setChecked(not is_checked)

            show_field = self.find_child_by_name('show')
            show_field.setChecked(is_checked)

            kiosk_field = self.find_child_by_name('kiosk')
            kiosk_field.setChecked(not is_checked)

            fullscreen_field = self.find_child_by_name('fullscreen')
            fullscreen_field.setChecked(not is_checked)

            always_on_top_field = self.find_child_by_name('always_on_top')
            always_on_top_field.setChecked(is_checked)

            resizable_field = self.find_child_by_name('resizable')
            resizable_field.setChecked(not is_checked)

    def setting_changed(self, obj, setting, *args):
        """
        If a setting changes in the GUI, this method will set the
        corresponding data to the same value. It will also update any
        json files in order to persist the changes.
        """

        if (setting.type == 'string' or
                setting.type == 'file' or
                setting.type == 'folder' or
                setting.type == 'int'):
            if args:
                setting.value = args[0]
            else:
                setting.value = obj.toPlainText()

            if not setting.value:
                setting.value = setting.default_value
        elif setting.type == 'strings':
            setting.value = args[0].split(',')
            setting.value = [x.strip() for x in setting.value if x]
            if not setting.value:
                setting.value = setting.default_value
        elif setting.type == 'check':
            setting.value = obj.isChecked()
            check_action = setting.check_action
            if hasattr(self, check_action):
                getattr(self, check_action)(obj.isChecked())
        elif setting.type == 'list':
            setting.value = obj.currentText()
            if not setting.value:
                setting.value = setting.default_value
        elif setting.type == 'range':
            setting.value = obj.value()

        if setting.action is not None:
            action = getattr(self, setting.action, None)
            if callable(action):
                action()

        self.write_package_json()

        self.ex_button.setEnabled(self.required_settings_filled())

    def project_path_changed(self, _):
        """If the project path changes, this checks to see if it's valid."""
        self.ex_button.setEnabled(self.required_settings_filled(True))

        dirs_filled_out = False
        if self.project_dir() and self.output_dir():
            if os.path.exists(self.project_dir()):
                dirs_filled_out = True

        self.option_settings_enabled(dirs_filled_out)

    def create_check_setting(self, name):
        """Create a generic checkbox setting in the GUI."""
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        check = QtGui.QCheckBox()

        check.setObjectName(setting.name)

        check.clicked.connect(self.call_with_object('setting_changed',
                                                    check, setting))
        check.setChecked(setting.value or False)
        check.setStatusTip(setting.description)
        check.setToolTip(setting.description)

        hlayout.addWidget(check)

        return hlayout

    def create_list_setting(self, name):
        """Create a generic list combobox setting from the setting name."""
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
        """
        Create a generic range setting with a slider based on the
        setting values.
        """
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
        slider.setValue(setting.default_value or 0)
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
        """Update the range label for a setting created with
        `create_range_setting`.
        """
        label.setText(str(value))

    def load_package_json(self, json_path=None):
        setting_list = super(MainWindow, self).load_package_json(json_path)
        for setting in setting_list:
            setting_field = self.find_child_by_name(setting.name)
            if setting_field:
                if (setting.type == 'file' or
                        setting.type == 'string' or
                        setting.type == 'folder' or
                        setting.type == 'int'):
                    val_str = self.convert_val_to_str(setting.value)
                    if hasattr(setting_field, 'setText'):
                        setting_field.setText(setting.filter_name(val_str))
                    elif hasattr(setting_field, 'setPlainText'):
                        setting_field.setPlainText(setting.filter_name(val_str))
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


def main():
    app = QApplication(sys.argv)

    QCoreApplication.setApplicationName("Web2Executable")
    QCoreApplication.setApplicationVersion(__gui_version__)
    QCoreApplication.setOrganizationName("SimplyPixelated")
    QCoreApplication.setOrganizationDomain("simplypixelated.com")

    frame = MainWindow(900, 500, app)
    frame.show_and_raise()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
