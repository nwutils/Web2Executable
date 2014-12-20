from utils import log, open_folder_in_explorer

import os
import glob
import sys

from PySide import QtGui, QtCore
from PySide.QtGui import QApplication
from PySide.QtNetwork import QHttp
from PySide.QtCore import QUrl, QFile, QIODevice


from command_line import CWD, CommandBase


class BackgroundThread(QtCore.QThread):
    def __init__(self, widget, method_name, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.widget = widget
        self.method_name = method_name

    def run(self):
        if hasattr(self.widget, self.method_name):
            func = getattr(self.widget, self.method_name)
            func()


class MainWindow(QtGui.QWidget, CommandBase):

    def update_nw_versions(self, button):
        self.get_versions_in_background()

    def __init__(self, width, height, parent=None):
        super(MainWindow, self).__init__(parent)
        CommandBase.__init__(self)
        self.output_package_json = True
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        self.update_json = False

        self.setup_nw_versions()

        self.thread = None
        self.original_packagejson = {}

        self.resize(width, height)

        self.extract_error = None

        self.create_application_layout()

        self.option_settings_enabled(False)

        self.setWindowTitle("Web2Executable")
        self.update_nw_versions(None)

    def setup_nw_versions(self):
        nw_version = self.get_setting('nw_version')
        try:
            f = open(os.path.join(CWD, 'files', 'nw-versions.txt'))
            for line in f:
                nw_version.values.append(line.strip())
        except IOError:
            nw_version.values.append(nw_version.default_value)

    def create_application_layout(self):
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(10, 5, 10, 5)

        self.create_layout_widgets()

        self.addWidgets_to_main_layout()

        self.setLayout(self.main_layout)

    def create_layout_widgets(self):
        self.download_bar_widget = self.create_download_bar()
        self.app_settings_widget = self.create_application_settings()
        self.win_settings_widget = self.create_window_settings()
        self.ex_settings_widget = self.create_export_settings()
        self.dl_settings_widget = self.create_download_settings()
        self.directory_chooser_widget = self.create_directory_choose()

    def addWidgets_to_main_layout(self):
        self.main_layout.addWidget(self.directory_chooser_widget)
        self.main_layout.addWidget(self.app_settings_widget)
        self.main_layout.addWidget(self.win_settings_widget)
        self.main_layout.addWidget(self.ex_settings_widget)
        self.main_layout.addWidget(self.dl_settings_widget)
        self.main_layout.addLayout(self.download_bar_widget)

    def option_settings_enabled(self, is_enabled):
        self.ex_button.setEnabled(is_enabled)
        self.app_settings_widget.setEnabled(is_enabled)
        self.win_settings_widget.setEnabled(is_enabled)
        self.ex_settings_widget.setEnabled(is_enabled)
        self.dl_settings_widget.setEnabled(is_enabled)

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
        QtGui.QMessageBox.information(self, 'Error!', str(exception))

    def disable_ui_while_working(self):
        self.option_settings_enabled(False)
        self.directory_chooser_widget.setEnabled(False)

    def enable_ui(self):
        self.option_settings_enabled(True)
        self.directory_chooser_widget.setEnabled(True)

    def required_settings_filled(self):
        proj_dir = self.project_dir()
        out_dir = self.output_dir()

        if proj_dir and out_dir:
            if os.path.exists(proj_dir):
                valid_proj_dirs = True

        settings_valid = True
        for sgroup in self.settings['setting_groups']:
            for sname, setting in sgroup.items():
                setting_path = os.path.join(self.project_dir(),
                                            str(setting.value))

                if setting.required and not setting.value:
                    return False

                if (setting.type == 'file' and
                    setting.value and
                        not os.path.exists(setting_path)):
                    log(setting.value, "does not exist")
                    settings_valid = False

                if (setting.type == 'folder' and
                    setting.value and
                        not os.path.exists(setting_path)):
                    settings_valid = False

        export_chosen = False
        for setting_name, setting in self.settings['export_settings'].items():
            if setting.value:
                export_chosen = True

        return export_chosen and valid_proj_dirs and settings_valid

    def project_dir(self):
        if hasattr(self, 'input_line'):
            return self.input_line.text()
        return ''

    def output_dir(self):
        if hasattr(self, 'output_line'):
            return self.output_line.text()
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
        open_export_button.setIcon(QtGui.QIcon(os.path.join('files', 'images', 'folder_open.png')))
        open_export_button.setToolTip('Open Export Folder')
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
            self.show_error('Download failed: {}.'.format(response_header.reasonPhrase()))
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

        if error:
            self.out_file.remove()
            self.show_error('Download failed: {}.'.format(self.http.errorString()))
            self.enable_ui_after_error()

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
        self.progress_label.setText(str(value))

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

    def done_making_files(self):
        self.ex_button.setEnabled(self.required_settings_filled())
        self.progress_text = 'Done Exporting.'
        self.enable_ui()
        self.delete_files()
        if self.output_err:
            self.show_error(self.output_err)
            self.enable_ui_after_error()

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

    def update_progress_bar(self, bytes_read, total_bytes):
        if self.http_request_aborted:
            return
        self.progress_bar.setMaximum(total_bytes)
        self.progress_bar.setValue(bytes_read)

    def download_file(self, path, setting):
        version_file = self.settings['base_url'].format(self.selected_version())
        self.progress_text = 'Downloading {}'.format(path.replace(version_file, ''))

        location = self.get_setting('download_dir').value

        url = QUrl(path)
        file_name = setting.save_file_path(self.selected_version(), location)

        archive_exists = QFile.exists(file_name)

        dest_files_exist = False

        # for dest_file in setting.dest_files:
        #    dest_file_path = os.path.join('files', setting.name, dest_file)
        #    dest_files_exist &= QFile.exists(dest_file_path)

        forced = self.get_setting('force_download').value

        if (archive_exists or dest_files_exist) and not forced:
            self.continue_downloading_or_extract()
            return

        self.out_file = QFile(file_name)
        if not self.out_file.open(QIODevice.WriteOnly):
            error = self.out_file.error_string()
            self.show_error('Unable to save the file {}: {}.'.format(file_name,
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
            path = '/'

        # Download the file.
        self.http_get_id = self.http.get(path, self.out_file)

    def create_directory_choose(self):
        group_box = QtGui.QGroupBox("Choose Your Web Project")

        input_layout = QtGui.QHBoxLayout()

        input_label = QtGui.QLabel('Project Directory:')
        self.input_line = QtGui.QLineEdit()
        self.input_line.textChanged.connect(self.project_path_changed)
        input_button = QtGui.QPushButton('...')
        input_button.clicked.connect(self.browse_dir)

        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(input_button)

        output_layout = QtGui.QHBoxLayout()

        output_label = QtGui.QLabel('Output Directory:')
        self.output_line = QtGui.QLineEdit()
        self.output_line.textChanged.connect(self.project_path_changed)
        output_button = QtGui.QPushButton('...')
        output_button.clicked.connect(self.browse_out_dir)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(output_button)

        vlayout = QtGui.QVBoxLayout()

        vlayout.setSpacing(5)
        vlayout.setContentsMargins(10, 5, 10, 5)

        vlayout.addLayout(input_layout)
        vlayout.addLayout(output_layout)

        group_box.setLayout(vlayout)

        return group_box

    def call_with_object(self, name, obj, *args, **kwargs):
        """Allows arguments to be passed to click events"""
        def call():
            if hasattr(self, name):
                func = getattr(self, name)
                func(obj, *args, **kwargs)
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
        return self.find_child_by_name('name').text()

    def browse_dir(self):
        self.update_json = False
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Find Project Directory",
                self.project_dir() or QtCore.QDir.currentPath())
        if directory:
            self.reset_settings()
            self.input_line.setText(directory)
            self.output_line.setText(os.path.join(directory, 'output'))

            proj_name = os.path.basename(directory)

            setting_input = self.find_child_by_name('main')
            files = (glob.glob(os.path.join(directory, 'index.html')) +
                     glob.glob(os.path.join(directory, 'index.php')) +
                     glob.glob(os.path.join(directory, 'index.htm')))
            if not setting_input.text():
                if files:
                    setting_input.setText(files[0].replace(self.project_dir() + os.path.sep, ''))

            app_name_input = self.find_child_by_name('name')
            title_input = self.find_child_by_name('title')
            if not app_name_input.text():
                app_name_input.setText(proj_name)
            if not title_input.text():
                title_input.setText(proj_name)

            self.load_package_json()
            self.open_export_button.setEnabled(True)
            self.update_json = True

    def browse_out_dir(self):
        self.update_json = False
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Choose Output Directory",
                                                             (self.output_line.text() or
                                                              self.project_dir() or
                                                              QtCore.QDir.currentPath()))
        if directory:
            self.output_line.setText(directory)
            self.update_json = True

    def get_file(self, obj, text_obj, setting, *args, **kwargs):
        file_path, _ = QtGui.QFileDialog.getOpenFileName(self, 'Choose File',
                                                         (setting.last_value or
                                                          self.project_dir() or
                                                          QtCore.QDir.currentPath()),
                                                         setting.file_types)
        if file_path:
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
        group_box = QtGui.QGroupBox("Application Settings")
        vlayout = self.create_layout(self.settings['order']['application_setting_order'])

        group_box.setLayout(vlayout)
        return group_box

    def create_setting(self, name):
        setting = self.get_setting(name)
        if setting.type == 'string':
            return self.create_text_input_setting(name)
        elif setting.type == 'file':
            return self.create_text_input_with_file_setting(name)
        elif setting.type == 'folder':
            return self.create_text_input_with_folder_setting(name)
        elif setting.type == 'check':
            return self.create_check_setting(name)
        elif setting.type == 'list':
            return self.create_list_setting(name)

    def create_window_settings(self):
        group_box = QtGui.QGroupBox("Window Settings")
        vlayout = self.create_layout(self.settings['order']['window_setting_order'])

        group_box.setLayout(vlayout)
        return group_box

    def create_export_settings(self):
        group_box = QtGui.QGroupBox("Export to")
        vlayout = self.create_layout(self.settings['order']['export_setting_order'], cols=4)

        group_box.setLayout(vlayout)
        return group_box

    def create_download_settings(self):
        group_box = QtGui.QGroupBox("Download Settings")
        vlayout = self.create_layout(self.settings['order']['download_setting_order'], 2)

        group_box.setLayout(vlayout)
        return group_box

    def create_layout(self, settings, cols=3):
        glayout = QtGui.QGridLayout()
        glayout.setContentsMargins(10, 5, 10, 5)
        glayout.setSpacing(10)
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
            glayout.addWidget(setting_label, row, col)
            glayout.addLayout(self.create_setting(setting_name),
                               row, col+1)
            col += 2

        return glayout

    def create_text_input_setting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.get_setting(name)

        text = QtGui.QLineEdit()
        text.setObjectName(setting.name)

        text.textChanged.connect(self.call_with_object('setting_changed',
                                                        text, setting))
        if setting.value:
            text.setText(str(setting.value))

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
            text.setText(str(setting.value))

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
            text.setText(str(setting.value))

        text.textChanged.connect(self.call_with_object('setting_changed',
                                                     text, setting))

        hlayout.addWidget(text)
        hlayout.addWidget(button)

        return hlayout

    def reset_settings(self):
        for sgroup in self.settings['setting_groups']:
            for setting in sgroup.values():
                widget = self.find_child_by_name(setting.name)

                if (setting.type == 'string' or
                    setting.type == 'file' or
                        setting.type == 'folder'):
                    old_val = ''

                    if setting.default_value is not None:
                        old_val = setting.default_value

                    setting.value = old_val.replace('\\', '\\\\')
                    widget.setText(str(old_val))

                elif setting.type == 'check':
                    old_val = False

                    if setting.default_value is not None:
                        old_val = setting.default_value

                    setting.value = old_val
                    widget.setChecked(old_val)

    def setting_changed(self, obj, setting, *args, **kwargs):
        if (setting.type == 'string' or
            setting.type == 'file' or
                setting.type == 'folder'):
            setting.value = obj.text().replace('\\', '\\\\')
            setting.value = obj.text()
        elif setting.type == 'check':
            setting.value = obj.isChecked()
        elif setting.type == 'list':
            setting.value = obj.currentText()

        if self.update_json:
            json_file = os.path.join(self.project_dir(), 'package.json')

            with open(json_file, 'w+') as f:
                f.write(self.generate_json())

        self.ex_button.setEnabled(self.required_settings_filled())

    def project_path_changed(self):
        self.ex_button.setEnabled(self.required_settings_filled())

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

        for val in setting.values:
            combo.addItem(val)

        default_index = combo.findText(setting.default_value)
        if default_index != -1:
            combo.setCurrentIndex(default_index)

        hlayout.addWidget(combo)
        if button:
            hlayout.addWidget(button)

        return hlayout

    def load_package_json(self):
        setting_list = super(MainWindow, self).load_package_json()
        for setting in setting_list:
            setting_field = self.find_child_by_name(setting.name)
            if setting_field:
                if (setting.type == 'file' or
                    setting.type == 'string' or
                        setting.type == 'folder'):
                    val_str = self.convert_val_to_str(setting.value)
                    setting_field.setText(val_str)
                if setting.type == 'check':
                    setting_field.setChecked(setting.value)
                if setting.type == 'list':
                    val_str = self.convert_val_to_str(setting.value)
                    index = setting_field.findText(val_str)
                    if index != -1:
                        setting_field.setCurrentIndex(index)
        self.ex_button.setEnabled(self.required_settings_filled())

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    frame = MainWindow(800, 500)
    frame.show_and_raise()

    sys.exit(app.exec_())
