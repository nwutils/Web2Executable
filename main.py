from utils import zip_files, join_files, log, get_temp_dir
import sys, os, glob, json, re, shutil, stat, tarfile, zipfile, traceback, platform
from PySide import QtGui, QtCore
from PySide.QtGui import QApplication
from PySide.QtNetwork import QHttp
from PySide.QtCore import QUrl, QFileInfo, QFile, QIODevice
from zipfile import ZipFile
from tarfile import TarFile

inside_mac_app = getattr(sys, 'frozen', '')

if inside_mac_app:
    CWD = os.path.dirname(sys.executable)
    os.chdir(CWD)
else:
    CWD = os.getcwd()

TEMP_DIR = get_temp_dir()


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
    def __init__(self, name='', display_name=None, value=None, required=False, type=None, file_types=None, *args, **kwargs):
        self.name = name
        self.display_name = display_name if display_name else name.replace('_',' ').capitalize()
        self.value = value
        self.required = required
        self.type = type
        self.file_types = file_types

        self.default_value = kwargs.pop('default_value', None)

        self.set_extra_attributes_from_keyword_args(kwargs)

        if self.value is None:
            self.value = self.default_value

        self.save_path = kwargs.pop('save_path', TEMP_DIR)

        self.get_file_information_from_url()

    def get_file_information_from_url(self):
        if hasattr(self, 'url'):
            self.file_name = self.url.split('/')[-1]
            self.full_file_path = os.path.join(self.save_path, self.file_name)
            self.file_ext = os.path.splitext(self.file_name)[1]
            if self.file_ext == '.zip':
                self.extract_class = ZipFile
                self.extract_args = ()
            elif self.file_ext == '.gz':
                self.extract_class = TarFile.open
                self.extract_args = ('r:gz',)

    def set_extra_attributes_from_keyword_args(self, kwargs):
        for undefined_key, undefined_value in kwargs.items():
            setattr(self, undefined_key, undefined_value)

    def get_file_bytes(self):
        fbytes = None
        file = self.extract_class(self.full_file_path, *self.extract_args)
        if self.file_ext == '.gz':
            fbytes = file.extractfile(self.extract_file).read()
        elif self.file_ext == '.zip':
            fbytes = file.read(self.extract_file)
        return fbytes

    def __repr__(self):
        return 'Setting: (name={}, display_name={}, value={}, required={}, type={})'.format(self.name, self.display_name, self.value, self.required, self.type)


class MainWindow(QtGui.QWidget):

    base_url = 'http://node-webkit.s3-website-us-east-1.amazonaws.com/v0.9.2/'

    app_settings = {'main': Setting(name='main', display_name='Main file', required=True, type='file', file_types='*.html *.php *.htm'),
                'name': Setting(name='name', display_name='App Name', required=True, type='string'),
                'description': Setting(name='description', default_default_value='', type='string'),
                'version': Setting(name='version', default_value='0.1.0', type='string'),
                'keywords':Setting(name='keywords', default_value='', type='string'),
                'nodejs': Setting('nodejs', 'Include Nodejs', default_value=True, type='check'),
                'node-main': Setting('node-main', 'Custom Nodejs Path', default_value='', type='file', file_types='*.js'),
                'single-instance': Setting('single-instance', 'Single Instance', default_value=True, type='check')}

    webkit_settings = {'plugin': Setting('plugin', 'Load plugins', default_value=False, type='check'),
                       'java': Setting('java', 'Load Java', default_value=False, type='check'),
                       'page-cache': Setting('page-cache', 'Enable Page Cache', default_value=False, type='check')}

    window_settings = {'title': Setting(name='title', default_value='', type='string'),
                       'icon': Setting('icon', 'Window Icon', default_value='', type='file', file_types='*.png *.jpg *.jpeg'),
                       'width': Setting('width', default_value=640, type='string'),
                       'height': Setting('height', default_value=480, type='string'),
                       'min_width': Setting('min_width', default_value=None, type='string'),
                       'min_height': Setting('min_height', default_value=None, type='string'),
                       'max_width': Setting('max_width', default_value=None, type='string'),
                       'max_height': Setting('max_height', default_value=None, type='string'),
                       'toolbar': Setting('toolbar', 'Show Toolbar', default_value=False, type='check'),
                       'always-on-top': Setting('always-on-top', 'Always on top', default_value=False, type='check'),
                       'frame': Setting('frame', 'Show Window Frame', default_value=True, type='check'),
                       'show_in_taskbar': Setting('show_in_taskbar', 'Show In Taskbar', default_value=True, type='check'),
                       'visible': Setting('visible', default_value=True, type='check'),
                       'resizable': Setting('resizable', default_value=False, type='check'),
                       'fullscreen': Setting('fullscreen', default_value=False, type='check')}

    export_settings = {'windows': Setting('windows', default_value=False, type='check',
                                          url=base_url+'node-webkit-v0.9.2-win-ia32.zip',
                                          extract_file='nw.exe',
                                          dest_file='nw.exe'),
                       'mac': Setting('mac', default_value=False, type='check',
                                      url=base_url+'node-webkit-v0.9.2-osx-ia32.zip',
                                      extract_file='node-webkit.app/Contents/Frameworks/node-webkit Framework.framework/node-webkit Framework',
                                      dest_file=os.path.join('node-webkit.app','Contents',
                                                                'Frameworks','node-webkit Framework.framework',
                                                                'node-webkit Framework')),
                       'linux-x64': Setting('linux-x64', default_value=False, type='check',
                                            url=base_url+'node-webkit-v0.9.2-linux-x64.tar.gz',
                                            extract_file='node-webkit-v0.9.2-linux-x64/nw',
                                            dest_file='nw'),
                       'linux-x32': Setting('linux-x32', default_value=False, type='check',
                                            url=base_url+'node-webkit-v0.9.2-linux-ia32.tar.gz',
                                            extract_file='node-webkit-v0.9.2-linux-ia32/nw',
                                            dest_file='nw')}

    _setting_groups = [app_settings, webkit_settings, window_settings, export_settings]

    application_setting_order = ['main', 'node-main', 'name', 'description', 'version', 'keywords',
                                 'nodejs', 'single-instance', 'plugin',
                                 'java', 'page-cache']

    window_setting_order = ['title', 'icon', 'width', 'height', 'min_width', 'min_height',
                            'max_width', 'max_height', 'toolbar', 'always-on-top', 'frame',
                            'show_in_taskbar', 'visible', 'resizable', 'fullscreen']

    export_setting_order = ['windows', 'linux-x64', 'mac', 'linux-x32']

    def __init__(self, width, height, parent=None):
        super(MainWindow, self).__init__(parent)

        self.httpGetId = 0
        self.httpRequestAborted = False
        self.thread = None
        self.original_packagejson = {}

        self.resize(width,height)

        self.extract_error = None

        self.create_application_layout()

        self.option_settings_enabled(False)

        self.setWindowTitle("Web2Executable")

    def create_application_layout(self):
        self.main_layout = QtGui.QVBoxLayout()

        self.create_layout_widgets()

        self.add_widgets_to_main_layout()

        self.setLayout(self.main_layout)

    def create_layout_widgets(self):
        self.download_bar_widget = self.createDownloadBar()
        self.app_settings_widget = self.createApplicationSettings()
        self.win_settings_widget = self.createWindowSettings()
        self.ex_settings_widget = self.createExportSettings()
        self.directory_chooser_widget = self.createDirectoryChoose()

    def add_widgets_to_main_layout(self):
        self.main_layout.addWidget(self.directory_chooser_widget)
        self.main_layout.addWidget(self.app_settings_widget)
        self.main_layout.addWidget(self.win_settings_widget)
        self.main_layout.addWidget(self.ex_settings_widget)
        self.main_layout.addLayout(self.download_bar_widget)

    def option_settings_enabled(self, is_enabled):
        self.ex_button.setEnabled(is_enabled)
        self.app_settings_widget.setEnabled(is_enabled)
        self.win_settings_widget.setEnabled(is_enabled)
        self.ex_settings_widget.setEnabled(is_enabled)

    def export(self, export_button, cancel_button):
        self.get_files_to_download()
        self.try_to_download_files()

    def get_files_to_download(self):
        self.files_to_download = []
        for setting_name, setting in self.export_settings.items():
            if setting.value == True:
                self.files_to_download.append(setting)

    def try_to_download_files(self):
        if self.files_to_download:
            self.progress_bar.setVisible(True)
            self.cancel_button.setEnabled(True)
            self.disableUIWhileWorking()

            self.download_file_with_error_handling()
        else:
            #This shouldn't happen since we disable the UI if there are no options selected
            #But in the weird event that this does happen, we are prepared!
            QtGui.QMessageBox.information(self, 'Export Options Empty!', 'Please choose one of the export options!')

    def download_file_with_error_handling(self):
        setting = self.files_to_download.pop()
        try:
            self.downloadFile(setting.url, setting)
        except Exception as e:
            if os.path.exists(setting.full_file_path):
                os.remove(setting.full_file_path)

            error = ''.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
            self.show_error(error)

    def show_error(self, exception):
        QtGui.QMessageBox.information(self, 'Error!', str(exception))

    def disableUIWhileWorking(self):
        self.option_settings_enabled(False)
        self.directory_chooser_widget.setEnabled(False)

    def enableUI(self):
        self.option_settings_enabled(True)
        self.directory_chooser_widget.setEnabled(True)

    def requiredSettingsFilled(self):
        proj_dir = self.projectDir()
        out_dir = self.outputDir()

        valid_proj_dir = False

        if proj_dir and out_dir:
            if os.path.exists(proj_dir):
                valid_proj_dirs = True

        settings_valid = True
        for sgroup in self._setting_groups:
            for sname, setting in sgroup.items():
                if setting.required and not setting.value:
                    return False
                if setting.type == 'file' and setting.value and not os.path.exists(os.path.join(self.projectDir(),setting.value)):
                    log(setting.value, "does not exist")
                    settings_valid = False

        export_chosen = False
        for setting_name, setting in self.export_settings.items():
            if setting.value:
                export_chosen = True


        return export_chosen and valid_proj_dirs and settings_valid

    def projectDir(self):
        if hasattr(self, 'input_line'):
            return self.input_line.text()
        return ''

    def outputDir(self):
        if hasattr(self, 'output_line'):
            return self.output_line.text()
        return ''

    def createDownloadBar(self):
        hlayout = QtGui.QHBoxLayout()

        vlayout = QtGui.QVBoxLayout()

        progress_label = QtGui.QLabel('')
        progress_bar = QtGui.QProgressBar()
        progress_bar.setVisible(False)

        vlayout.addWidget(progress_label)
        vlayout.addWidget(progress_bar)
        vlayout.addWidget(QtGui.QLabel(''))

        ex_button = QtGui.QPushButton('Export')
        ex_button.setEnabled(False)

        cancel_button = QtGui.QPushButton('Cancel Download')
        cancel_button.setEnabled(False)

        ex_button.clicked.connect(self.callWithObject('export', ex_button, cancel_button))
        cancel_button.clicked.connect(self.cancelDownload)

        buttonBox = QtGui.QDialogButtonBox()
        buttonBox.addButton(cancel_button, QtGui.QDialogButtonBox.RejectRole)
        buttonBox.addButton(ex_button, QtGui.QDialogButtonBox.AcceptRole)

        hlayout.addLayout(vlayout)
        hlayout.addWidget(buttonBox)

        self.progress_label = progress_label
        self.progress_bar = progress_bar
        self.cancel_button = cancel_button

        http = QHttp(self)
        http.requestFinished.connect(self.httpRequestFinished)
        http.dataReadProgress.connect(self.updateProgressBar)
        http.responseHeaderReceived.connect(self.readResponseHeader)
        self.http = http
        self.ex_button = ex_button

        return hlayout

    def readResponseHeader(self, response_header):
        # Check for genuine error conditions.
        if response_header.statusCode() not in (200, 300, 301, 302, 303, 307):
            self.show_error('Download failed: {}.'.format(response_header.reasonPhrase()))
            self.httpRequestAborted = True
            self.http.abort()

    def httpRequestFinished(self, requestId, error):
        if requestId != self.httpGetId:
            return

        if self.httpRequestAborted:
            if self.outFile is not None:
                self.outFile.close()
                self.outFile.remove()
                self.outFile = None
            return

        self.outFile.close()

        if error:
            self.outFile.remove()
            self.show_error('Download failed: {}.'.format(self.http.errorString()))

        self.continueDownloadingOrExtract()

    def continueDownloadingOrExtract(self):
        if self.files_to_download:
            setting = self.files_to_download.pop()
            self.downloadFile(setting.url, setting)
        else:
            self.progress_text = 'Done.'
            self.cancel_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.extractFilesInBackground()

    @property
    def progress_text(self):
        return self.progress_label.text()

    @progress_text.setter
    def progress_text(self, value):
        self.progress_label.setText(str(value))

    def runInBackground(self, method_name, callback):

        self.thread = BackgroundThread(self, method_name)
        self.thread.finished.connect(callback)
        self.thread.start()

    def makeOutputFilesInBackground(self):
        self.ex_button.setEnabled(False)

        self.runInBackground('makeOutputDirs', self.doneMakingFiles)

    def doneMakingFiles(self):
        self.ex_button.setEnabled(True)
        self.progress_text = 'Done Exporting.'
        self.enableUI()
        if self.output_err:
            self.show_error(self.output_err)

    def extractFilesInBackground(self):
        self.progress_text = 'Extracting.'
        self.ex_button.setEnabled(False)

        self.runInBackground('extractFiles', self.doneExtracting)

    def extractFiles(self):
        self.extract_error = None
        for setting_name, setting in self.export_settings.items():
            try:
                if setting.value:
                    extract_path = os.path.join('files', setting.name)

                    if not os.path.exists(os.path.join(extract_path, setting.dest_file)):
                        fbytes = setting.get_file_bytes()

                        with open(os.path.join(extract_path, setting.dest_file), 'wb+') as d:
                            d.write(fbytes)
                        if os.path.exists(setting.full_file_path):
                            os.remove(setting.full_file_path) #remove the zip/tar since we don't need it anymore

                    self.progress_text += '.'

            except (tarfile.ReadError, zipfile.BadZipfile) as e:
                if os.path.exists(setting.full_file_path):
                    os.remove(setting.full_file_path)
                self.extract_error = e
                #cannot use GUI in thread to notify user. Save it for later



    def doneExtracting(self):
        self.ex_button.setEnabled(True)
        if self.extract_error:
            self.progress_text = 'Error extracting.'
            self.show_error('There were one or more errors with your zip/tar files. They were deleted. Please try to export again.')
        else:
            self.progress_text = 'Done extracting.'
            self.makeOutputFilesInBackground()

    def cancelDownload(self):
        self.progress_text = 'Download cancelled.'
        self.cancel_button.setEnabled(False)
        self.httpRequestAborted = True
        self.http.abort()
        self.enableUI()

    def updateProgressBar(self, bytesRead, totalBytes):
        if self.httpRequestAborted:
            return
        self.progress_bar.setMaximum(totalBytes)
        self.progress_bar.setValue(bytesRead)

    def downloadFile(self, path, setting):
        self.progress_text = 'Downloading {}'.format(path.replace(self.base_url,''))

        url = QUrl(path)
        fileInfo = QFileInfo(url.path())
        fileName = setting.full_file_path

        if QFile.exists(fileName) or QFile.exists(os.path.join('files', setting.name, setting.dest_file)):
            self.continueDownloadingOrExtract()
            return #QFile.remove(fileName)

        self.outFile = QFile(fileName)
        if not self.outFile.open(QIODevice.WriteOnly):
            self.show_error('Unable to save the file {}: {}.'.format(fileName, self.outFile.errorString()))
            self.outFile = None
            self.enableUI()
            return

        mode = QHttp.ConnectionModeHttp
        port = url.port()
        if port == -1:
            port = 0
        self.http.setHost(url.host(), mode, port)
        self.httpRequestAborted = False

        path = QUrl.toPercentEncoding(url.path(), "!$&'()*+,;=:@/")
        if path:
            path = str(path)
        else:
            path = '/'

        # Download the file.
        self.httpGetId = self.http.get(path, self.outFile)

    def createDirectoryChoose(self):
        groupBox = QtGui.QGroupBox("Choose Your Web Project")

        input_layout = QtGui.QHBoxLayout()

        input_label = QtGui.QLabel('Project Directory:')
        self.input_line = QtGui.QLineEdit()
        self.input_line.textChanged.connect(self.projectPathChanged)
        input_button = QtGui.QPushButton('...')
        input_button.clicked.connect(self.browseDir)

        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(input_button)

        output_layout = QtGui.QHBoxLayout()

        output_label = QtGui.QLabel('Output Directory:')
        self.output_line = QtGui.QLineEdit()
        self.output_line.textChanged.connect(self.projectPathChanged)
        output_button = QtGui.QPushButton('...')
        output_button.clicked.connect(self.browseOutDir)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(output_button)

        vlayout = QtGui.QVBoxLayout()
        vlayout.addLayout(input_layout)
        vlayout.addLayout(output_layout)

        groupBox.setLayout(vlayout)

        return groupBox

    def callWithObject(self, name, obj, *args, **kwargs):
        """Allows arguments to be passed to click events"""
        def call():
            if hasattr(self, name):
                func = getattr(self, name)
                func(obj, *args, **kwargs)
        return call

    def findChildByName(self, name):
        return self.findChild(QtCore.QObject, name)

    def findAllChildren(self, names):
        children = []
        for child in self.findChildren(QtCore.QObject):
            if child.objectName() in names:
                children.append(child)

        return children

    def projectName(self):
        return self.findChildByName('name').text()

    def browseDir(self):
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Find Project Directory",
                self.projectDir() or QtCore.QDir.currentPath())
        if directory:
            self.resetSettings()
            self.input_line.setText(directory)
            self.output_line.setText(os.path.join(directory,'output'))

            proj_name = os.path.basename(directory)

            setting_input = self.findChildByName('main')
            files = glob.glob(os.path.join(directory,'index.html')) + glob.glob(os.path.join(directory,'index.php')) + glob.glob(os.path.join(directory,'index.htm'))
            if not setting_input.text():
                if files:
                    setting_input.setText(files[0])

            app_name_input = self.findChildByName('name')
            title_input = self.findChildByName('title')
            if not app_name_input.text():
                app_name_input.setText(proj_name)
            if not title_input.text():
                title_input.setText(proj_name)

            self.loadPackageJson()

    def browseOutDir(self):
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Choose Output Directory",
                self.projectDir() or QtCore.QDir.currentPath())
        if directory:
            self.output_line.setText(directory)

    def getFile(self, obj, text_obj, setting, *args, **kwargs):
        file, junk = QtGui.QFileDialog.getOpenFileName(self, 'Choose File', self.projectDir() or QtCore.QDir.currentPath(), setting.file_types)
        if file:
            text_obj.setText(file)


    def createApplicationSettings(self):
        groupBox = QtGui.QGroupBox("Application Settings")
        vlayout = self.createLayout(self.application_setting_order)

        groupBox.setLayout(vlayout)
        return groupBox

    def createSetting(self, name):
        setting = self.getSetting(name)
        if setting.type == 'string':
            return self.createTextInputSetting(name)
        elif setting.type == 'file':
            return self.createTextInputWithFileSetting(name)
        elif setting.type == 'check':
            return self.createCheckSetting(name)


    def createWindowSettings(self):
        groupBox = QtGui.QGroupBox("Window Settings")
        vlayout = self.createLayout(self.window_setting_order)

        groupBox.setLayout(vlayout)
        return groupBox

    def createExportSettings(self):
        groupBox = QtGui.QGroupBox("Export to")
        vlayout = self.createLayout(self.export_setting_order)

        groupBox.setLayout(vlayout)
        return groupBox

    def createLayout(self, settings, cols=2):
        hlayout = QtGui.QHBoxLayout()

        layouts = []

        for i in xrange(cols):
            l = QtGui.QFormLayout()
            l.setSpacing(10)
            l.setVerticalSpacing(10)
            layouts.append(l)

        col = 0
        row = 0

        for setting_name in settings:
            setting = self.getSetting(setting_name)
            if col >= cols:
                row += 1
                col = 0
            vlayout = layouts[col]
            display_name = setting.display_name+':'
            if setting.required:
                display_name += '*'
            vlayout.addRow(display_name, self.createSetting(setting_name))
            col += 1

        for l in layouts:
            hlayout.addLayout(l)
        hlayout.setSpacing(20)
        return hlayout

    def createTextInputSetting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.getSetting(name)

        text = QtGui.QLineEdit()
        text.setObjectName(setting.name)

        text.textChanged.connect(self.callWithObject('settingChanged', text, setting))
        if setting.value:
            text.setText(str(setting.value))

        hlayout.addWidget(text)

        return hlayout

    def createTextInputWithFileSetting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.getSetting(name)

        text = QtGui.QLineEdit()
        text.setObjectName(setting.name)

        button = QtGui.QPushButton('...')
        button.setMaximumWidth(30)
        button.setMaximumHeight(26)

        button.clicked.connect(self.callWithObject('getFile', button, text, setting))

        if setting.value:
            text.setText(str(setting.value))

        text.textChanged.connect(self.callWithObject('settingChanged', text, setting))

        hlayout.addWidget(text)
        hlayout.addWidget(button)

        return hlayout

    def resetSettings(self):
        for sgroup in self._setting_groups:
            for setting in sgroup.values():
                widget = self.findChildByName(setting.name)
                if setting.type == 'string' or setting.type == 'file':
                    old_val = ''
                    if setting.default_value is not None:
                        old_val = setting.default_value
                    setting.value = old_val
                    widget.setText(str(old_val))
                elif setting.type == 'check':
                    old_val = False
                    if setting.default_value is not None:
                        old_val = setting.default_value
                    setting.value = old_val
                    widget.setChecked(old_val)


    def settingChanged(self, obj, setting, *args, **kwargs):
        if setting.type == 'string' or setting.type == 'file':
            setting.value = obj.text()
        elif setting.type == 'check':
            setting.value = obj.isChecked()

        self.ex_button.setEnabled(self.requiredSettingsFilled())

    def projectPathChanged(self):
        self.ex_button.setEnabled(self.requiredSettingsFilled())

        dirs_filled_out = False
        if self.projectDir() and self.outputDir():
            if os.path.exists(self.projectDir()):
                dirs_filled_out = True

        self.app_settings_widget.setEnabled(dirs_filled_out)
        self.win_settings_widget.setEnabled(dirs_filled_out)
        self.ex_settings_widget.setEnabled(dirs_filled_out)

    def getSetting(self, name):
        for setting_group in self._setting_groups:
            if name in setting_group:
                setting = setting_group[name]
                return setting


    def createCheckSetting(self, name):
        hlayout = QtGui.QHBoxLayout()

        setting = self.getSetting(name)

        check = QtGui.QCheckBox()

        check.setObjectName(setting.name)

        check.clicked.connect(self.callWithObject('settingChanged', check, setting))
        check.setChecked(setting.value)

        hlayout.addWidget(check)

        return hlayout

    def generate_json(self):
        if 'webkit' not in self.original_packagejson:
            self.original_packagejson['webkit'] = {}
        if 'window' not in self.original_packagejson:
            self.original_packagejson['window'] = {}

        dic = self.original_packagejson

        for setting_name, setting in self.app_settings.items():
            if setting.value is not None:
                dic[setting_name] = setting.value
                if setting_name == 'keywords':
                    dic[setting_name] = re.findall("\w+", setting.value)


        for setting_name, setting in self.window_settings.items():
            if setting.value is not None:
                if 'height' in setting.name or 'width' in setting.name:
                    try:
                        dic['window'][setting_name] = int(setting.value)
                    except ValueError:
                        pass
                else:
                    dic['window'][setting_name] = setting.value

        for setting_name, setting in self.webkit_settings.items():
            if setting.value is not None:
                dic['webkit'][setting_name] = setting.value

        s = json.dumps(dic, indent=4)

        return s

    def loadPackageJson(self):
        p_json = glob.glob(os.path.join(self.projectDir(), 'package.json'))
        if p_json:
            json_str = ''
            with open(p_json[0], 'r') as f:
                json_str = f.read()
            try:
                self.load_from_json(json_str)
            except ValueError: #Json file is invalid
                log( 'Warning: Json file invalid.')


    def load_from_json(self, json_str):
        dic = json.loads(json_str)
        self.original_packagejson = dic
        stack = [('root',dic)]
        while stack:
            parent, new_dic = stack.pop()
            for item in new_dic:
                setting_field = self.findChildByName(item)
                setting = self.getSetting(item)
                if setting_field:
                    if setting.type == 'file' or setting.type == 'string':
                        val_str = self.convert_val_to_str(new_dic[item])
                        setting_field.setText(val_str)
                        setting.value = val_str
                    if setting.type == 'check':
                        setting_field.setChecked(new_dic[item])
                        setting.value = new_dic[item]
                if isinstance(new_dic[item], dict):
                    stack.append((item,new_dic[item]))

    def convert_val_to_str(self, val):
        if isinstance(val, (list,tuple)):
            return ', '.join(val)
        return str(val)

    def copyFilesToProjectFolder(self):
        old_dir = CWD
        os.chdir(self.projectDir())
        for sgroup in self._setting_groups:
            for setting in sgroup.values():
                if setting.type == 'file' and setting.value:
                    try:
                        shutil.copy(setting.value, self.projectDir())
                        setting.value = os.path.basename(setting.value)
                    except shutil.Error as e:#same file warning
                        log( 'Warning: {}'.format(e))

        os.chdir(old_dir)

    def makeOutputDirs(self):
        self.output_err = ''
        try:
            self.progress_text = 'Removing old output directory...'

            outputDir = os.path.join(self.outputDir(), self.projectName())
            tempDir = os.path.join(TEMP_DIR, 'webexectemp')
            if os.path.exists(tempDir):
                shutil.rmtree(tempDir)

            self.progress_text = 'Making new directories...'

            if not os.path.exists(outputDir):
                os.makedirs(outputDir)

            os.makedirs(tempDir)

            self.copyFilesToProjectFolder()

            json_file = os.path.join(self.projectDir(), 'package.json')

            with open(json_file, 'w+') as f:
                f.write(self.generate_json())

            zip_file = os.path.join(tempDir, self.projectName()+'.nw')

            zip_files(zip_file, self.projectDir(), exclude_paths=[outputDir])
            for ex_setting in self.export_settings.values():
                if ex_setting.value:
                    self.progress_text = 'Making files for {}'.format(ex_setting.display_name)
                    export_dest = os.path.join(outputDir, ex_setting.name)

                    if os.path.exists(export_dest):
                        shutil.rmtree(export_dest)

                    #shutil will make the directory for us
                    shutil.copytree(os.path.join('files', ex_setting.name), export_dest)
                    self.progress_text += '.'

                    if ex_setting.name == 'mac':
                        app_path = os.path.join(export_dest, self.projectName()+'.app')
                        shutil.move(os.path.join(export_dest, 'node-webkit.app'), app_path)

                        self.progress_text += '.'

                        shutil.copy(zip_file, os.path.join(app_path, 'Contents', 'Resources', 'app.nw'))

                        self.progress_text += '.'
                    else:
                        ext = ''
                        if ex_setting.name == 'windows':
                            ext = '.exe'

                        nw_path = os.path.join(export_dest, ex_setting.dest_file)
                        dest_binary_path = os.path.join(export_dest, self.projectName()+ext)
                        join_files(os.path.join(export_dest, self.projectName()+ext), nw_path, zip_file)

                        sevenfivefive = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
                        os.chmod(dest_binary_path, sevenfivefive)

                        self.progress_text += '.'

                        if os.path.exists(nw_path):
                            os.remove(nw_path)

        except Exception as e:
            self.output_err += ''.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
        finally:
            shutil.rmtree(tempDir)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    frame = MainWindow(700, 500)
    frame.show_and_raise()

    sys.exit(app.exec_())
