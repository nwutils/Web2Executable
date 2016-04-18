'''Command line module for web2exe.'''

import ssl

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

from utils import zip_files, join_files, log, get_temp_dir
from pycns import save_icns
from pepy.pe import PEFile

import argparse
import urllib.request as request
import platform
import re
import time
import sys
import os
import glob
import json
import shutil
import stat
import tarfile
import zipfile
import traceback
import subprocess
import logging
import logging.handlers as lh
import plistlib
import codecs
from pprint import pprint

from utils import get_data_path, get_data_file_path
import utils

from semantic_version import Version

from zipfile import ZipFile
from tarfile import TarFile

from io import StringIO

from configobj import ConfigObj

COMMAND_LINE = True



inside_packed_exe = getattr(sys, 'frozen', '')

if inside_packed_exe:
    # we are running in a |PyInstaller| bundle
    CWD = os.path.dirname(sys.executable)
else:
    # we are running in a normal Python environment
    CWD = os.getcwd()

def get_file(path):
    parts = path.split('/')
    independent_path = utils.path_join(CWD, *parts)
    return independent_path

def is_installed():
    uninst = get_file('uninst.exe')
    return utils.is_windows() and os.path.exists(uninst)

__version__ = "v0.0.0"

with open(get_file('files/version.txt')) as f:
    __version__ = f.read().strip()


TEMP_DIR = get_temp_dir()
DEFAULT_DOWNLOAD_PATH = get_data_path('files/downloads')

logger = logging.getLogger('W2E logger')
LOG_FILENAME = get_data_file_path('files/error.log')
if __name__ != '__main__':
    logging.basicConfig(
        filename=LOG_FILENAME,
        format=("%(levelname) -10s %(asctime)s %(module)s.py: "
                "%(lineno)s %(funcName)s - %(message)s"),
        level=logging.DEBUG
    )
    logger = logging.getLogger('W2E logger')

handler = lh.RotatingFileHandler(LOG_FILENAME, maxBytes=100000, backupCount=2)
logger.addHandler(handler)

def my_excepthook(type_, value, tback):
    output_err = u''.join([x for x in traceback.format_exception(type_, value, tback)])
    logger.error(u'{}'.format(output_err))
    sys.__excepthook__(type_, value, tback)

sys.excepthook = my_excepthook


try:
    os.makedirs(DEFAULT_DOWNLOAD_PATH)
except:
    pass


def get_base_url():
    url = None
    try:
        url = codecs.open(get_file('files', 'base_url.txt'), encoding='utf-8').read().strip()
    except (OSError, IOError):
        url = 'http://dl.node-webkit.org/v{}/'
    return url


class Setting(object):
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
        if hasattr(self.filter_action, text):
            action = getattr(self.filter_action, text)
            return action(text)
        return text

    def get_file_information_from_url(self):
        if hasattr(self, 'url'):
            self.file_name = self.url.split(u'/')[-1]
            self.full_file_path = utils.path_join(self.save_path, self.file_name)
            self.file_ext = os.path.splitext(self.file_name)[1]
            if self.file_ext == '.zip':
                self.extract_class = ZipFile
                self.extract_args = ()
            elif self.file_ext == '.gz':
                self.extract_class = TarFile.open
                self.extract_args = ('r:gz',)

    def save_file_path(self, version, location=None, sdk_build=False):
        if location:
            self.save_path = location
        else:
            self.save_path = self.save_path or DEFAULT_DOWNLOAD_PATH


        self.get_file_information_from_url()

        if self.full_file_path:

            path = self.full_file_path.format(version)

            versions = re.findall('(\d+)\.(\d+)\.(\d+)', version)[0]

            minor = int(versions[1])
            major = int(versions[0])

            if minor >= 12 or major > 0:
                path = path.replace('node-webkit', 'nwjs')

            if minor >= 13 and sdk_build:
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
            dir_name = utils.path_join(ex_path, os.path.basename(path).replace('.tar.gz',''))
        else:
            dir_name = utils.path_join(ex_path, os.path.basename(path).replace('.zip',''))

        if os.path.exists(dir_name):
            for p in os.listdir(dir_name):
                abs_file = utils.path_join(dir_name, p)
                utils.move(abs_file, ex_path)
            utils.rmtree(dir_name, ignore_errors=True)

    def __repr__(self):
        url = ''
        if hasattr(self, 'url'):
            url = self.url
        return (u'Setting: (name={}, '
                u'display_name={}, '
                u'value={}, required={}, '
                u'type={}, url={})').format(self.name,
                                           self.display_name,
                                           self.value,
                                           self.required,
                                           self.type,
                                           url)


class CommandBase(object):
    def __init__(self):
        self.quiet = False
        self.logger = None
        self.output_package_json = True
        self.settings = self.get_settings()
        self._project_dir = ''
        self._output_dir = ''
        self._progress_text = ''
        self._output_err = ''
        self._extract_error = ''
        self._project_name = None
        self.original_packagejson = {}

    def init(self):
        self.logger = logging.getLogger('CMD logger')
        self.update_nw_versions(None)
        self.setup_nw_versions()

    def update_nw_versions(self, button):
        self.progress_text = 'Updating nw versions...'
        self.get_versions()
        self.progress_text = '\nDone.\n'

    def setup_nw_versions(self):
        nw_version = self.get_setting('nw_version')
        nw_version.values = []
        try:
            f = codecs.open(get_data_file_path('files/nw-versions.txt'), encoding='utf-8')
            for line in f:
                nw_version.values.append(line.strip())
            f.close()
        except IOError:
            nw_version.values.append(nw_version.default_value)

    def get_nw_versions(self):
        nw_version = self.get_setting('nw_version')
        return nw_version.values[:]

    def get_settings(self):
        config_file = get_file('files/settings.cfg')
        contents = codecs.open(config_file, encoding='utf-8').read()
        contents = contents.replace(u'{DEFAULT_DOWNLOAD_PATH}',
                                    DEFAULT_DOWNLOAD_PATH)
        config_io = StringIO(contents)
        config = ConfigObj(config_io, unrepr=True).dict()
        settings = {'setting_groups': []}
        setting_items = (list(config['setting_groups'].items()) +
                         [('export_settings', config['export_settings'])] +
                         [('compression', config['compression'])])
        for setting_group, setting_group_dict in setting_items:
            settings[setting_group] = {}
            for setting_name, setting_dict in setting_group_dict.items():
                for key, val in setting_dict.items():
                    if '_callback' in key:
                        setting_dict[key] = getattr(self, setting_dict[key])
                setting_obj = Setting(name=setting_name, **setting_dict)
                settings[setting_group][setting_name] = setting_obj

        sgroup_items = config['setting_groups'].items()
        for setting_group, setting_group_dict in sgroup_items:
            settings['setting_groups'].append(settings[setting_group])

        self._setting_items = (list(config['setting_groups'].items()) +
                         [('export_settings', config['export_settings'])] +
                         [('compression', config['compression'])])
        config.pop('setting_groups')
        config.pop('export_settings')
        config.pop('compression')
        self._setting_items += config.items()
        for key, val in config.items():
            settings[key] = val

        return settings

    def project_dir(self):
        return self._project_dir

    def output_dir(self):
        return self._output_dir

    def project_name(self):
        return (self._project_name or
                os.path.basename(os.path.abspath(self.project_dir())))

    def get_setting(self, name):
        for setting_group in (self.settings['setting_groups'] +
                              [self.settings['export_settings']] +
                              [self.settings['compression']]):
            if name in setting_group:
                setting = setting_group[name]
                return setting

    def get_settings_type(self, type):
        settings = []
        for setting_group in (self.settings['setting_groups'] +
                              [self.settings['export_settings']] +
                              [self.settings['compression']]):
            for name, setting in setting_group.items():
                if setting.type == type:
                    settings.append(setting)
        return settings

    def show_error(self, error):
        if self.logger is not None:
            self.logger.error(error)

    def enable_ui_after_error(self):
        pass

    def get_versions(self):
        if self.logger is not None:
            self.logger.info('Getting versions...')

        union_versions = set()

        for url in self.settings['version_info']['urls']:
            response = request.urlopen(url)
            html = response.read().decode('utf-8')

            nw_version = self.get_setting('nw_version')

            old_versions = set(nw_version.values)
            old_versions = old_versions.union(union_versions)
            new_versions = set(re.findall('(\S+) / \d{2}-\d{2}-\d{4}', html))

            union_versions = old_versions.union(new_versions)

        versions = sorted(union_versions,
                          key=Version, reverse=True)

        if len(versions) > 19:
            #Cut off old versions
            versions = versions[:-19]

        nw_version.values = versions
        f = None
        try:
            f = codecs.open(get_data_file_path('files/nw-versions.txt'), 'w', encoding='utf-8')
            for v in nw_version.values:
                f.write(v+os.linesep)
            f.close()
        except IOError:
            error = u''.join([x for x in traceback.format_exception(sys.exc_info()[0],
                                                                             sys.exc_info()[1],
                                                                             sys.exc_info()[2])])
            self.show_error(error)
            self.enable_ui_after_error()
        finally:
            if f:
                f.close()

    def download_file_with_error_handling(self):
        setting = self.files_to_download.pop()
        location = self.get_setting('download_dir').value
        version = self.selected_version()
        path = setting.url.format(version, version)
        versions = re.findall('(\d+)\.(\d+)\.(\d+)', version)[0]

        sdk_build_setting = self.get_setting('sdk_build')
        sdk_build = sdk_build_setting.value

        minor = int(versions[1])
        major = int(versions[0])
        if minor >= 12 or major > 0:
            path = path.replace('node-webkit', 'nwjs')

        if minor >= 13 and sdk_build:
            path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

        try:
            return self.download_file(setting.url.format(version, version),
                                      setting)
        except (Exception, KeyboardInterrupt):
            if os.path.exists(setting.save_file_path(version, location)):
                os.remove(setting.save_file_path(version, location))

            error = u''.join([x for x in traceback.format_exception(sys.exc_info()[0],
                                                                             sys.exc_info()[1],
                                                                             sys.exc_info()[2])])
            self.show_error(error)
            self.enable_ui_after_error()

    def load_package_json(self, json_path=None):
        self.logger.info('Loading package.json')
        if json_path is not None:
            p_json = [json_path]
        else:
            p_json = glob.glob(utils.path_join(self.project_dir(),
                                            'package.json'))
        setting_list = []
        if p_json:
            json_str = ''
            try:
                with codecs.open(p_json[0], 'r', encoding='utf-8') as f:
                    json_str = f.read()
            except IOError:
                return setting_list
            try:
                setting_list = self.load_from_json(json_str)
            except ValueError as e:  # Json file is invalid
                self.logger.warning('Warning: Json file invalid.')
                self.progress_text = u'{}\n'.format(e)
        return setting_list

    def generate_json(self, global_json=False):
        self.logger.info('Generating package.json...')

        dic = {'webexe_settings': {}}

        versions = self.get_version_tuple()
        major_ver = versions[0]
        minor_ver = versions[1]

        if not global_json:
            dic.update({'webkit': {}, 'window': {}})
            dic.update(self.original_packagejson)
            for setting_name, setting in self.settings['app_settings'].items():
                if (major_ver > 0 or minor_ver >= 13) and setting_name != 'node-remote':
                    dic.pop(setting_name, '')
                    setting_name = setting_name.replace('-', '_')

                if setting.value is not None and setting.value != '':
                    dic[setting_name] = setting.value
                    if setting_name == 'keywords':
                        dic[setting_name] = re.findall('\w+', setting.value)
                else:
                    dic.pop(setting_name, '')

            for setting_name, setting in self.settings['window_settings'].items():
                if major_ver > 0 or minor_ver >= 13:
                    dic['window'].pop(setting_name, '')
                    setting_name = setting_name.replace('-', '_')
                if setting.value is not None and setting.value != '':
                    if 'height' in setting.name or 'width' in setting.name:
                        try:
                            dic['window'][setting_name] = int(setting.value)
                        except ValueError:
                            pass
                    else:
                        dic['window'][setting_name] = setting.value
                else:
                    dic['window'].pop(setting_name, '')

            for setting_name, setting in self.settings['webkit_settings'].items():
                if major_ver > 0 or minor_ver >= 13:
                    dic['webkit'].pop(setting_name, '')
                    setting_name = setting_name.replace('-', '_')
                if setting.value is not None and setting.value != '':
                    dic['webkit'][setting_name] = setting.value
                else:
                    dic['webkit'].pop(setting_name, '')

        if not global_json:
            dl_export_items = (list(self.settings['download_settings'].items()) +
                               list(self.settings['export_settings'].items()) +
                               list(self.settings['compression'].items()) +
                               list(self.settings['web2exe_settings'].items()))
        else:
            dl_export_items = (list(self.settings['download_settings'].items()) +
                               list(self.settings['export_settings'].items()) +
                               list(self.settings['compression'].items()))

        for setting_name, setting in dl_export_items:
            if setting.value is not None:
                dic['webexe_settings'][setting_name] = setting.value

        s = json.dumps(dic, indent=4)

        return s

    @property
    def extract_error(self):
        return self._extract_error

    @extract_error.setter
    def extract_error(self, value):
        if value is not None and not self.quiet and COMMAND_LINE:
            self._extract_error = value
            sys.stderr.write(u'\r{}'.format(self._extract_error))
            sys.stderr.flush()

    @property
    def output_err(self):
        return self._output_err

    @output_err.setter
    def output_err(self, value):
        if value is not None and not self.quiet and COMMAND_LINE:
            self._output_err = value
            sys.stderr.write(u'\r{}'.format(self._output_err))
            sys.stderr.flush()

    @property
    def progress_text(self):
        return self._progress_text

    @progress_text.setter
    def progress_text(self, value):
        if value is not None and not self.quiet and COMMAND_LINE:
            self._progress_text = value
            sys.stdout.write(u'\r{}'.format(self._progress_text))
            sys.stdout.flush()

    def load_from_json(self, json_str):
        dic = json.loads(json_str)
        self.original_packagejson.update(dic)
        setting_list = []
        stack = [('root', dic)]
        while stack:
            parent, new_dic = stack.pop()
            for item in new_dic:
                setting = self.get_setting(item)
                if setting:
                    setting_list.append(setting)
                    if (setting.type == 'file' or
                        setting.type == 'string' or
                            setting.type == 'folder'):
                        val_str = self.convert_val_to_str(new_dic[item])
                        setting.value = val_str
                    if setting.type == 'strings':
                        strs = self.convert_val_to_str(new_dic[item]).split(',')
                        setting.value = strs
                    if setting.type == 'check':
                        setting.value = new_dic[item]
                    if setting.type == 'list':
                        val_str = self.convert_val_to_str(new_dic[item])
                        setting.value = val_str
                    if setting.type == 'range':
                        setting.value = new_dic[item]
                if isinstance(new_dic[item], dict):
                    stack.append((item, new_dic[item]))
        return setting_list

    def selected_version(self):
        return self.get_setting('nw_version').value

    def extract_files(self):
        self.extract_error = None
        location = self.get_setting('download_dir').value

        sdk_build_setting = self.get_setting('sdk_build')
        sdk_build = sdk_build_setting.value
        version = self.selected_version()

        for setting_name, setting in self.settings['export_settings'].items():
            save_file_path = setting.save_file_path(version,
                                                    location,
                                                    sdk_build)
            try:
                if setting.value:
                    extract_path = get_data_path('files/'+setting.name)
                    setting.extract(extract_path, version, sdk_build)

                    self.progress_text += '.'

            except (tarfile.ReadError, zipfile.BadZipfile) as e:
                if os.path.exists(save_file_path):
                    os.remove(save_file_path)
                self.extract_error = e
                self.logger.error(self.extract_error)
                # cannot use GUI in thread to notify user. Save it for later
        self.progress_text = '\nDone.\n'
        return True

    def create_icns_for_app(self, icns_path):
        icon_setting = self.get_setting('icon')
        mac_app_icon_setting = self.get_setting('mac_icon')
        icon_path = (mac_app_icon_setting.value
                     if mac_app_icon_setting.value
                     else icon_setting.value)

        if icon_path:
            icon_path = utils.path_join(self.project_dir(), icon_path)
            if not icon_path.endswith('.icns'):
                save_icns(icon_path, icns_path)
            else:
                utils.copy(icon_path, icns_path)

    def replace_icon_in_exe(self, exe_path):
        icon_setting = self.get_setting('icon')
        exe_icon_setting = self.get_setting('exe_icon')
        icon_path = (exe_icon_setting.value
                     if exe_icon_setting.value
                     else icon_setting.value)
        if icon_path:
            p = PEFile(exe_path)
            p.replace_icon(utils.path_join(self.project_dir(), icon_path))
            p.write(exe_path)
            p = None

    def write_package_json(self):
        json_file = utils.path_join(self.project_dir(), 'package.json')

        global_json = utils.get_data_file_path('files/global.json')

        if self.output_package_json:
            with codecs.open(json_file, 'w+', encoding='utf-8') as f:
                f.write(self.generate_json())


        with codecs.open(global_json, 'w+', encoding='utf-8') as f:
            f.write(self.generate_json(global_json=True))

    def clean_dirs(self, *dirs):
        for directory in dirs:
            if os.path.exists(directory):
                utils.rmtree(directory, onerror=self.remove_readonly)
            if not os.path.exists(directory):
                os.makedirs(directory)

    def handle_mac_export(self, export_dest):
        app_path = utils.path_join(export_dest,
                                   self.project_name()+'.app')

        try:
            utils.move(utils.path_join(export_dest,
                                       'nwjs.app'),
                       app_path)
        except IOError:
            utils.move(utils.path_join(export_dest,
                                       'node-webkit.app'),
                       app_path)

        plist_path = utils.path_join(app_path, 'Contents', 'Info.plist')

        plist_dict = plistlib.readPlist(plist_path)

        plist_dict['CFBundleDisplayName'] = self.project_name()
        plist_dict['CFBundleName'] = self.project_name()
        version_setting = self.get_setting('version')
        plist_dict['CFBundleShortVersionString'] = version_setting.value
        plist_dict['CFBundleVersion'] = version_setting.value

        plistlib.writePlist(plist_dict, plist_path)

        self.progress_text += '.'

        app_nw_res = utils.path_join(app_path,
                                     'Contents',
                                     'Resources',
                                     'app.nw')

        if uncompressed:
            utils.copytree(app_loc, app_nw_res)
        else:
            utils.copy(app_loc, app_nw_res)

        if minor_ver >= 13 or major_ver > 0:
            self.create_icns_for_app(utils.path_join(app_path,
                                                     'Contents',
                                                     'Resources',
                                                     'app.icns'))
            self.create_icns_for_app(utils.path_join(app_path,
                                                     'Contents',
                                                     'Resources',
                                                     'document.icns'))
            strings_path = utils.path_join(app_path,
                                           'Contents',
                                           'Resources',
                                           'en.lproj',
                                           'InfoPlist.strings')

            strings = open(strings_path, mode='rb').read()
            strings = str(strings)
            strings = strings.replace('nwjs', self.project_name())
            with open(strings_path, mode='wb+') as f:
                f.write(bytes(strings, 'utf-8'))

        else:
            self.create_icns_for_app(utils.path_join(app_path,
                                                     'Contents',
                                                     'Resources',
                                                     'nw.icns'))

        self.progress_text += '.'

    def get_export_dest(self, ex_setting, output_dir):
        export_dest = utils.path_join(output_dir, ex_setting.name)

        versions = self.get_version_tuple()
        major_ver, minor_ver, _ = versions

        if minor_ver >= 12 or major_ver > 0:
            export_dest = export_dest.replace('node-webkit', 'nwjs')

        return export_dest

    def copy_export_files(self, ex_setting, export_dest):
        if os.path.exists(export_dest):
            utils.rmtree(export_dest)

        # shutil will make the directory for us
        utils.copytree(get_data_path('files/'+ex_setting.name),
                       export_dest,
                        ignore=shutil.ignore_patterns('place_holder.txt'))
        utils.rmtree(get_data_path('files/'+ex_setting.name))

    def replace_localized_app_name(self, app_path):
        strings_path = utils.path_join(app_path,
                                       'Contents',
                                       'Resources',
                                       'en.lproj',
                                       'InfoPlist.strings')

        strings = open(strings_path, mode='rb').read()
        strings = str(strings)
        strings = strings.replace('nwjs', self.project_name())
        with open(strings_path, mode='wb+') as f:
            f.write(bytes(strings, 'utf-8'))

    def replace_plist(self, app_path):
        plist_path = utils.path_join(app_path, 'Contents', 'Info.plist')

        plist_dict = plistlib.readPlist(plist_path)

        plist_dict['CFBundleDisplayName'] = self.project_name()
        plist_dict['CFBundleName'] = self.project_name()
        version_setting = self.get_setting('version')
        plist_dict['CFBundleShortVersionString'] = version_setting.value
        plist_dict['CFBundleVersion'] = version_setting.value

        plistlib.writePlist(plist_dict, plist_path)

    def process_mac_setting(self, app_loc, export_dest, uncompressed):
        app_path = utils.path_join(export_dest,
                                   self.project_name()+'.app')

        try:
            utils.move(utils.path_join(export_dest,
                                       'nwjs.app'),
                       app_path)
        except IOError:
            utils.move(utils.path_join(export_dest,
                                       'node-webkit.app'),
                       app_path)

        self.replace_plist(app_path)

        app_nw_res = utils.path_join(app_path,
                                     'Contents',
                                     'Resources',
                                     'app.nw')

        if uncompressed:
            utils.copytree(app_loc, app_nw_res)
        else:
            utils.copy(app_loc, app_nw_res)

        self.progress_text += '.'

        versions = self.get_version_tuple()
        major_ver, minor_ver, _ = versions

        if minor_ver >= 13 or major_ver > 0:
            self.create_icns_for_app(utils.path_join(app_path,
                                                     'Contents',
                                                     'Resources',
                                                     'app.icns'))
            self.create_icns_for_app(utils.path_join(app_path,
                                                     'Contents',
                                                     'Resources',
                                                     'document.icns'))
            self.replace_localized_app_name(app_path)

        else:
            self.create_icns_for_app(utils.path_join(app_path,
                                                     'Contents',
                                                     'Resources',
                                                     'nw.icns'))

        self.progress_text += '.'


    def process_export_setting(self, ex_setting, output_dir,
                               temp_dir, app_loc, uncompressed):
        if ex_setting.value:
            self.progress_text = '\n'

            name = ex_setting.display_name

            self.progress_text = u'Making files for {}...'.format(name)

            export_dest = self.get_export_dest(ex_setting, output_dir)

            self.copy_export_files(ex_setting, export_dest)

            self.progress_text += '.'

            if 'mac' in ex_setting.name:
                self.process_mac_setting(app_loc, export_dest, uncompressed)
            else:
                nw_path = utils.path_join(export_dest,
                                          ex_setting.binary_location)

                ext = ''
                if 'windows' in ex_setting.name:
                    ext = '.exe'
                    self.replace_icon_in_exe(nw_path)

                self.compress_nw(nw_path)

                dest_binary_path = utils.path_join(export_dest,
                                                   self.project_name() +
                                                   ext)
                if 'linux' in ex_setting.name:
                    self.make_desktop_file(dest_binary_path, export_dest)

                self.copy_executable(export_dest, dest_binary_path,
                                     nw_path, app_loc, uncompressed)

                self.set_executable(dest_binary_path)

                self.progress_text += '.'

                if os.path.exists(nw_path):
                    os.remove(nw_path)



    def make_output_dirs(self):
        output_dir = utils.path_join(self.output_dir(), self.project_name())
        temp_dir = utils.path_join(TEMP_DIR, 'webexectemp')

        self.progress_text = 'Making new directories...\n'

        self.clean_dirs(temp_dir, output_dir)

        self.copy_files_to_project_folder()
        self.write_package_json()

        app_loc = self.get_app_nw_loc(temp_dir, output_dir)

        uncomp_setting = self.get_setting('uncompressed_folder')
        uncompressed = uncomp_setting.value

        for ex_setting in self.settings['export_settings'].values():
            self.process_export_setting(ex_setting, output_dir, temp_dir,
                                        app_loc, uncompressed)


    def try_make_output_dirs(self):
        self.output_err = ''
        try:
            self.make_output_dirs()
        except Exception:
            error = u''.join([x for x in traceback.format_exception(sys.exc_info()[0],
                                                                    sys.exc_info()[1],
                                                                    sys.exc_info()[2])])
            self.logger.error(error)
            self.output_err += error
        finally:
            temp_dir = utils.path_join(TEMP_DIR, 'webexectemp')
            utils.rmtree(temp_dir, onerror=self.remove_readonly)

    def get_app_nw_loc(self, temp_dir, output_dir):
        app_file = utils.path_join(temp_dir, self.project_name()+'.nw')

        uncomp_setting = self.get_setting('uncompressed_folder')
        uncompressed = uncomp_setting.value

        if uncompressed:
            app_nw_folder = utils.path_join(temp_dir, self.project_name()+'.nwf')

            utils.copytree(self.project_dir(), app_nw_folder,
                           ignore=shutil.ignore_patterns(output_dir))
            return app_nw_folder
        else:
            zip_files(app_file, self.project_dir(), exclude_paths=[output_dir])
            return app_file

    def get_version_tuple(self):
        strs = re.findall('(\d+)\.(\d+)\.(\d+)', self.selected_version())[0]
        return [int(s) for s in strs]

    def copy_executable(self, export_path, dest_path,
                        nw_path, app_loc, uncompressed):
        versions = self.get_version_tuple()
        major_ver, minor_ver, _ = versions

        if minor_ver >= 13 or major_ver > 0:
            package_loc = utils.path_join(export_path, 'package.nw')
            if uncompressed:
                utils.copytree(app_loc, package_loc)
                utils.copy(nw_path, dest_path)
            else:
                join_files(dest_path, nw_path, app_loc)
        else:
            join_files(dest_path, nw_path, app_loc)


    def set_executable(self, path):
        sevenfivefive = (stat.S_IRWXU |
                         stat.S_IRGRP |
                         stat.S_IXGRP |
                         stat.S_IROTH |
                         stat.S_IXOTH)
        os.chmod(path, sevenfivefive)

    def make_desktop_file(self, nw_path, export_dest):
        icon_set = self.get_setting('icon')
        icon_path = utils.path_join(self.project_dir(), icon_set.value)
        if os.path.exists(icon_path) and icon_set.value:
            utils.copy(icon_path, export_dest)
            icon_path = utils.path_join(export_dest, os.path.basename(icon_path))
        else:
            icon_path = ''
        name = self.project_name()
        pdir = self.project_dir()
        version = self.get_setting('version')
        desc = self.get_setting('description')
        dfile_path = utils.path_join(export_dest, u'{}.desktop'.format(name))
        file_str = (
                    u'[Desktop Entry]\n'
                    u'Version={}\n'
                    u'Name={}\n'
                    u'Comment={}\n'
                    u'Exec={}\n'
                    u'Icon={}\n'
                    u'Terminal=false\n'
                    u'Type=Application\n'
                    u'Categories=Utility;Application;\n'
                    )
        file_str = file_str.format(version.value,
                                   name,
                                   desc.value,
                                   nw_path,
                                   icon_path)
        with codecs.open(dfile_path, 'w+', encoding='utf-8') as f:
            f.write(file_str)

        os.chmod(dfile_path, 0o755)

    def compress_nw(self, nw_path):
        compression = self.get_setting('nw_compression_level')
        if compression.value == 0:
            return

        comp_dict = {'Darwin64bit': get_file('files/compressors/upx-mac'),
                     'Darwin32bit': get_file('files/compressors/upx-mac'),
                     'Linux64bit':  get_file('files/compressors/upx-linux-x64'),
                     'Linux32bit':  get_file('files/compressors/upx-linux-x32'),
                     'Windows64bit':  get_file('files/compressors/upx-win.exe'),
                     'Windows32bit':  get_file('files/compressors/upx-win.exe')
                     }

        if is_installed():
            comp_dict['Windows64bit'] = get_data_file_path('files/compressors/upx-win.exe')
            comp_dict['Windows32bit'] = get_data_file_path('files/compressors/upx-win.exe')

        plat = platform.system()+platform.architecture()[0]
        upx_version = comp_dict.get(plat, None)

        if upx_version is not None:
            upx_bin = upx_version
            os.chmod(upx_bin, 0o755)
            cmd = [upx_bin, '--lzma', u'-{}'.format(compression.value), nw_path]
            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        startupinfo=startupinfo)
            else:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
            self.progress_text = '\n\n'
            self.progress_text = 'Compressing files'
            while proc.poll() is None:
                self.progress_text += '.'
                time.sleep(2)
            output, err = proc.communicate()

    def remove_readonly(self, action, name, exc):
        try:
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
        except Exception as e:
            error = u'Failed to remove file: {}.'.format(name)
            error += '\nError recieved: {}'.format(e)
            self.logger.error(error)
            self.output_err += error

    def copy_files_to_project_folder(self):
        old_dir = CWD
        os.chdir(self.project_dir())
        self.logger.info(u'Copying files to {}'.format(self.project_dir()))
        for sgroup in self.settings['setting_groups']:
            for setting in sgroup.values():
                if setting.copy and setting.type == 'file' and setting.value:
                    f_path = setting.value.replace(self.project_dir(), '')
                    if os.path.isabs(f_path):
                        try:
                            utils.copy(setting.value, self.project_dir())
                            self.logger.info(u'Copying file {} to {}'.format(setting.value, self.project_dir()))
                        except shutil.Error as e:  # same file warning
                            self.logger.warning(u'Warning: {}'.format(e))
                        finally:
                            setting.value = os.path.basename(setting.value)

        os.chdir(old_dir)

    def convert_val_to_str(self, val):
        if isinstance(val, (list, tuple)):
            return ', '.join(val)
        return str(val).replace(self.project_dir()+os.path.sep, '')


    def run_script(self, script):
        if not script:
            return

        if os.path.exists(script):
            self.progress_text = 'Executing script {}...'.format(script)
            contents = ''
            with codecs.open(script, 'r', encoding='utf-8') as f:
                contents = f.read()

            _, ext = os.path.splitext(script)

            export_opts = self.get_export_options()
            export_dir = '{}{}{}'.format(self.output_dir(),
                                         os.path.sep,
                                         self.project_name())
            export_dirs = []
            for opt in export_opts:
                export_dirs.append('{}{}{}'.format(export_dir, os.path.sep, opt))

            command = None
            bat_file = None

            export_dict = {'mac-x64_dir': '',
                           'mac-x32_dir': '',
                           'windows-x64_dir': '',
                           'windows-x32_dir': '',
                           'linux-x64_dir': '',
                           'linux-x32_dir': ''}

            if ext == '.py':
                env_file = get_file('files/env_vars.py')
                env_contents = codecs.open(env_file, 'r', encoding='utf-8').read()

                for i, ex_dir in enumerate(export_dirs):
                    opt = export_opts[i]
                    export_dict[opt+'_dir'] = ex_dir

                env_vars = env_contents.format(proj_dir=self.project_dir(),
                                               proj_name=self.project_name(),
                                               export_dir=export_dir,
                                               export_dirs=str(export_dirs),
                                               num_dirs=len(export_dirs),
                                               **export_dict)
                pycontents = '{}\n{}'.format(env_vars, contents)

                command = ['python', '-c', pycontents]


            elif ext == '.bash':
                env_file = get_file('files/env_vars.bash')
                env_contents = codecs.open(env_file, 'r', encoding='utf-8').read()
                ex_dir_vars = ''

                for i, ex_dir in enumerate(export_dirs):
                    opt = export_opts[i]
                    export_dict[opt+'_dir'] = ex_dir

                for ex_dir in export_dirs:
                    ex_dir_vars += "'{}' ".format(ex_dir)

                env_vars = env_contents.format(proj_dir=self.project_dir(),
                                               proj_name=self.project_name(),
                                               export_dir=export_dir,
                                               num_dirs=len(export_dirs),
                                               export_dirs=ex_dir_vars,
                                               **export_dict)
                shcontents = '{}\n{}'.format(env_vars, contents)

                command = ['bash', '-c', shcontents]

            elif ext == '.bat':
                env_file = get_file('files/env_vars.bat')
                env_contents = codecs.open(env_file, 'r', encoding='utf-8').read()
                ex_dir_vars = ''

                for i, ex_dir in enumerate(export_dirs):
                    opt = export_opts[i]
                    export_dict[opt+'_dir'] = ex_dir
                    ex_dir_vars += 'set "EXPORT_DIRS[{}]={}"\n'.format(i, ex_dir)

                env_vars = env_contents.format(proj_dir=self.project_dir(),
                                               proj_name=self.project_name(),
                                               export_dir=export_dir,
                                               num_dirs=len(export_dirs),
                                               export_dirs=ex_dir_vars,
                                               **export_dict)
                batcontents = '{}\n{}'.format(env_vars, contents)

                bat_file = utils.path_join(TEMP_DIR, '{}.bat'.format(self.project_name()))

                self.logger.debug(batcontents)

                with open(bat_file, 'w+') as f:
                    f.write(batcontents)

                command = [bat_file]

            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = proc.communicate()
            output = output.strip()
            error = error.strip()

            if bat_file:
                os.remove(bat_file)

            with open(get_file('script-output.txt'), 'w+') as f:
                f.write('Output:\n{}'.format(output))
                if error:
                    f.write('\n\nErrors:\n{}\n'.format(error))

            self.progress_text = 'Done executing script.'
        else:
            self.progress_text = '\nThe script {} does not exist. Not running.'.format(script)


    def export(self):
        self.get_files_to_download()
        res = self.try_to_download_files()
        if res:
            self.make_output_dirs()
            script = self.get_setting('custom_script').value
            self.run_script(script)
            self.progress_text = '\nDone!\n'
            self.progress_text = u'Output directory is {}{}{}.\n'.format(self.output_dir(),
                                                                         os.path.sep,
                                                                         self.project_name())
            self.delete_files()

    def get_export_options(self):
        options = []
        for setting_name, setting in self.settings['export_settings'].items():
            if setting.value is True:
                options.append(setting_name)
        return options

    def get_files_to_download(self):
        self.files_to_download = []
        for setting_name, setting in self.settings['export_settings'].items():
            if setting.value is True:
                self.files_to_download.append(setting)
        return True

    def try_to_download_files(self):
        if self.files_to_download:
            return self.download_file_with_error_handling()

    def continue_downloading_or_extract(self):
        if self.files_to_download:
            return self.download_file_with_error_handling()
        else:
            self.progress_text = 'Extracting files.'
            return self.extract_files()

    def download_file(self, path, setting):
        self.logger.info(u'Downloading file {}.'.format(path))

        location = self.get_setting('download_dir').value

        sdk_build_setting = self.get_setting('sdk_build')
        sdk_build = sdk_build_setting.value

        versions = self.get_version_tuple()
        major, minor, _ = versions

        if minor >= 12 or major > 0:
            path = path.replace('node-webkit', 'nwjs')

        if minor >= 13 and sdk_build:
            path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

        url = path
        file_name = setting.save_file_path(self.selected_version(), location, sdk_build)
        tmp_file = list(os.path.split(file_name))
        tmp_file[-1] = '.tmp.' + tmp_file[-1]
        tmp_file = os.sep.join(tmp_file)
        tmp_size = 0

        archive_exists = os.path.exists(file_name)
        tmp_exists = os.path.exists(tmp_file)

        dest_files_exist = False

        forced = self.get_setting('force_download').value

        if (archive_exists or dest_files_exist) and not forced:
            self.logger.info(u'File {} already downloaded. Continuing...'.format(path))
            return self.continue_downloading_or_extract()
        elif tmp_exists and (os.stat(tmp_file).st_size > 0):
            tmp_size = os.stat(tmp_file).st_size
            headers = {'Range': 'bytes={}-'.format(tmp_size)}
            url = request.Request(url, headers=headers)

        web_file = request.urlopen(url)
        f = open(tmp_file, 'ab')
        meta = web_file.info()
        file_size = tmp_size + int(meta.getheaders("Content-Length")[0])

        version = self.selected_version()
        version_file = self.settings['base_url'].format(version)
        short_name = path.replace(version_file, '')
        MB = file_size/1000000.0
        downloaded = ''
        if tmp_size:
            self.progress_text = 'Resuming previous download...\n'
            self.progress_text = u'Already downloaded {:.2f} MB\n'.format(tmp_size/1000000.0)
        self.progress_text = (u'Downloading: {}, '
                              u'Size: {:.2f} MB {}\n'.format(short_name,
                                                         MB,
                                                         downloaded))

        file_size_dl = (tmp_size or 0)
        block_sz = 8192
        while True:
            buff = web_file.read(block_sz)
            if not buff:
                break

            file_size_dl += len(buff)
            DL_MB = file_size_dl/1000000.0
            percent = file_size_dl*100.0/file_size
            f.write(buff)
            args = (DL_MB, MB, percent)
            status = "{:10.2f}/{:.2f} MB  [{:3.2f}%]".format(*args)
            self.progress_text = status

        self.progress_text = '\nDone downloading.\n'
        f.close()
        try:
            os.rename(tmp_file, file_name)
        except OSError:
            if sys.platform.startswith('win32') and not(os.path.isdir(file_name)):
                os.remove(file_name)
                os.rename(tmp_file, file_name)
            else:
                os.remove(tmp_file)
                raise OSError

        return self.continue_downloading_or_extract()

    def delete_files(self):
        for ex_setting in self.settings['export_settings'].values():
            f_path = get_data_file_path('files/{}/'.format(ex_setting.name))
            if os.path.exists(f_path):
                utils.rmtree(f_path)


class ArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: {}\n'.format(message))
        self.print_help()
        sys.exit(2)

def unicode_arg(bytestring):
    return bytestring

def main():
    parser = ArgParser(description=('Command line interface '
                                    'to web2exe. {}'.format(__version__)),
                                     prog='web2execmd')
    command_base = CommandBase()
    command_base.init()
    parser.add_argument('project_dir', metavar='project_dir',
                        help='The project directory.', type=unicode_arg)
    parser.add_argument('--output-dir', dest='output_dir',
                        help='The output directory for exports.',
                        type=unicode_arg)
    parser.add_argument('--quiet', dest='quiet', action='store_true',
                        default=False,
                        help='Silences output messages')
    parser.add_argument('--verbose', dest='verbose', action='store_true',
                        default=False,
                        help=('Prints debug errors and messages instead '
                              'of logging to files/errors.log'))
    parser.add_argument('--package-json',
                        dest='load_json',
                        nargs='?',
                        default='',
                        const=True,
                        help=('Loads the package.json '
                              'file in the project directory. '
                              'Ignores other command line arguments.'))
    parser.add_argument('--cmd-version', action='version', version='%(prog)s {}'.format(__version__))

    for setting_group_dict in command_base.settings['setting_groups']+[command_base.settings['compression']]:
        for setting_name, setting in setting_group_dict.items():
            kwargs = {}
            if setting_name == 'name':
                kwargs.update({'default': command_base.project_name})
            else:
                kwargs.update({'required': setting.required,
                               'default': setting.default_value})
            action = 'store'
            option_name = setting_name.replace('_', '-')

            if setting.type in ['file', 'string', 'strings']:
                kwargs.update({'type': unicode_arg})

            if isinstance(setting.default_value, bool):
                action = ('store_true' if setting.default_value is False
                          else 'store_false')
                kwargs.update({'action': action})
                if setting.default_value is True:
                    option_name = u'disable-{}'.format(option_name)
            else:
                if setting.values:
                    kwargs.update({'choices': setting.values})
                    setting.description += u' Possible values: {{{}}}'.format(', '.join([str(x) for x in setting.values]))
                    kwargs.update({'metavar': ''})
                else:
                    kwargs.update({'metavar': '<{}>'.format(setting.display_name)})

            parser.add_argument(u'--{}'.format(option_name),
                                dest=setting_name,
                                help=setting.description,
                                **kwargs
                                )

    export_args = [arg for arg in command_base.settings['export_settings']]
    parser.add_argument('--export-to', dest='export_options',
                        nargs='+', required=True,
                        choices=export_args,
                        help=('Choose at least one system '
                              'to export to.'))

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(
            stream=sys.stdout,
            format=("%(levelname) -10s %(module)s.py: "
                    "%(lineno)s %(funcName)s - %(message)s"),
            level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            filename=LOG_FILENAME,
            format=("%(levelname) -10s %(asctime)s %(module)s.py: "
                    "%(lineno)s %(funcName)s - %(message)s"),
            level=logging.DEBUG
        )

    global logger
    global handler

    logger = logging.getLogger('CMD Logger')
    handler = lh.RotatingFileHandler(LOG_FILENAME, maxBytes=100000, backupCount=2)
    logger.addHandler(handler)

    def my_excepthook(type_, value, tback):
        output_err = u''.join([x for x in traceback.format_exception(type_, value, tback)])
        logger.error(u'{}'.format(output_err))
        sys.__excepthook__(type_, value, tback)

    sys.excepthook = my_excepthook

    command_base.logger = logger

    if args.quiet:
        command_base.quiet = True

    command_base._project_dir = args.project_dir

    command_base._output_dir = (args.output_dir or
                                utils.path_join(command_base._project_dir, 'output'))

    if args.app_name is None:
        args.app_name = command_base.project_name()

    if args.name is not None:
        setting = command_base.get_setting('name')
        args.name = setting.filter_name(args.name if not callable(args.name) else args.name())

    command_base._project_name = args.app_name if not callable(args.app_name) else args.app_name()

    if not args.title:
        args.title = command_base.project_name()

    for name, val in args._get_kwargs():
        if callable(val):
            val = val()
        if name == 'export_options':
            for opt in val:
                setting = command_base.get_setting(opt)
                if setting is not None:
                    setting.value = True
        else:
            setting = command_base.get_setting(name)
            if setting is not None:
                setting.value = val

    if args.load_json is True:
        command_base.load_package_json()
    elif args.load_json:
        command_base.load_package_json(args.load_json)

    command_base.export()

if __name__ == '__main__':
    main()
