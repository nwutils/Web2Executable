'''Command line module for web2exe.'''

__version__ = "v0.2.9b"

import ssl

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

from utils import zip_files, join_files, log, get_temp_dir
from pycns import save_icns
from pepy.pe import PEFile

import argparse
import urllib2
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

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

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
    output_err = u''.join(traceback.format_exception(type_, value, tback))
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
        action = unicode
        if hasattr(unicode, self.filter_action):
            action = getattr(unicode, self.filter_action)
        return action(unicode(text))

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

    def save_file_path(self, version, location=None):
        if location:
            self.save_path = location
        else:
            self.save_path = self.save_path or DEFAULT_DOWNLOAD_PATH


        self.get_file_information_from_url()

        if self.full_file_path:

            path = self.full_file_path.format(version)

            versions = re.findall('(\d+)\.(\d+)\.(\d+)', version)[0]

            minor = int(versions[1])
            if minor >= 12:
                path = path.replace('node-webkit', 'nwjs')

            return path

        return ''

    def extract_file_path(self, version):
        if self.extract_file:
            return self.extract_file.format(version)
        return u''

    def set_extra_attributes_from_keyword_args(self, **kwargs):
        for undefined_key, undefined_value in kwargs.items():
            setattr(self, undefined_key, undefined_value)

    def extract(self, ex_path, version):
        if os.path.exists(ex_path):
            shutil.rmtree(ex_path, ignore_errors=True)

        path = self.save_file_path(version)

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
                shutil.move(abs_file, ex_path)
            shutil.rmtree(dir_name, ignore_errors=True)

    def get_file_bytes(self, version):
        fbytes = []

        path = self.save_file_path(version)

        file = self.extract_class(path,
                                  *self.extract_args)
        for extract_path, dest_path in zip(self.extract_files,
                                           self.dest_files):
            new_bytes = None
            try:
                extract_p = extract_path.format(version)

                versions = re.findall('(\d+)\.(\d+)\.(\d+)', version)[0]

                minor = int(versions[1])
                if minor >= 12:
                    extract_p = extract_p.replace('node-webkit', 'nwjs')

                if self.file_ext == '.gz':
                    new_bytes = file.extractfile(extract_p).read()
                elif self.file_ext == '.zip':
                    new_bytes = file.read(extract_p)
            except KeyError as e:
                logger.error(unicode(e))
                # dirty hack to support old versions of nw
                if 'no item named' in unicode(e):
                    extract_path = '/'.join(extract_path.split('/')[1:])
                    try:
                        if self.file_ext == '.gz':
                            new_bytes = file.extractfile(extract_path).read()
                        elif self.file_ext == '.zip':
                            new_bytes = file.read(extract_path)
                    except KeyError as e:
                        logger.error(unicode(e))

            if new_bytes is not None:
                fbytes.append((dest_path, new_bytes))

        return fbytes

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
        setting_items = (config['setting_groups'].items() +
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

        self._setting_items = (config['setting_groups'].items() +
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

    def show_error(self, error):
        if self.logger is not None:
            self.logger.error(error)

    def enable_ui_after_error(self):
        pass

    def get_versions(self):
        if self.logger is not None:
            self.logger.info('Getting versions...')
        response = urllib2.urlopen(self.settings['version_info']['url'])
        html = response.read()

        nw_version = self.get_setting('nw_version')

        old_versions = set(nw_version.values)
        new_versions = set(re.findall('(\S+) / \S+', html))

        union_versions = list(old_versions.union(new_versions))

        versions = sorted(union_versions,
                          key=Version, reverse=True)

        nw_version.values = versions
        f = None
        try:
            f = codecs.open(get_data_file_path('files/nw-versions.txt'), 'w', encoding='utf-8')
            for v in nw_version.values:
                f.write(v+os.linesep)
            f.close()
        except IOError:
            error = u''.join(traceback.format_exception(sys.exc_info()[0],
                                                       sys.exc_info()[1],
                                                       sys.exc_info()[2]))
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

        minor = int(versions[1])
        if minor >= 12:
            path = path.replace('node-webkit', 'nwjs')

        try:
            return self.download_file(setting.url.format(version, version),
                                      setting)
        except (Exception, KeyboardInterrupt):
            if os.path.exists(setting.save_file_path(version, location)):
                os.remove(setting.save_file_path(version, location))

            error = u''.join(traceback.format_exception(sys.exc_info()[0],
                                                       sys.exc_info()[1],
                                                       sys.exc_info()[2]))
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

        if not global_json:
            dic.update({'webkit': {}, 'window': {}})
            dic.update(self.original_packagejson)
            for setting_name, setting in self.settings['app_settings'].items():
                if setting.value is not None:
                    dic[setting_name] = setting.value
                    if setting_name == 'keywords':
                        dic[setting_name] = re.findall("\w+", setting.value)

            for setting_name, setting in self.settings['window_settings'].items():
                if setting.value is not None:
                    if 'height' in setting.name or 'width' in setting.name:
                        try:
                            dic['window'][setting_name] = int(setting.value)
                        except ValueError:
                            pass
                    else:
                        dic['window'][setting_name] = setting.value

            for setting_name, setting in self.settings['webkit_settings'].items():
                if setting.value is not None:
                    dic['webkit'][setting_name] = setting.value

        if not global_json:
            dl_export_items = (self.settings['download_settings'].items() +
                               self.settings['export_settings'].items() +
                               self.settings['compression'].items() +
                               self.settings['web2exe_settings'].items())
        else:
            dl_export_items = (self.settings['download_settings'].items() +
                               self.settings['export_settings'].items() +
                               self.settings['compression'].items())

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
            self._extract_error = unicode(value)
            sys.stderr.write(u'\r{}'.format(self._extract_error))
            sys.stderr.flush()

    @property
    def output_err(self):
        return self._output_err

    @output_err.setter
    def output_err(self, value):
        if value is not None and not self.quiet and COMMAND_LINE:
            self._output_err = unicode(value)
            sys.stderr.write(u'\r{}'.format(self._output_err))
            sys.stderr.flush()

    @property
    def progress_text(self):
        return self._progress_text

    @progress_text.setter
    def progress_text(self, value):
        if value is not None and not self.quiet and COMMAND_LINE:
            self._progress_text = unicode(value)
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
        version = self.selected_version()
        for setting_name, setting in self.settings['export_settings'].items():
            save_file_path = setting.save_file_path(version,
                                                    location)
            try:
                if setting.value:
                    extract_path = get_data_path('files/'+setting.name)
                    setting.extract(extract_path, version)

                    #if os.path.exists(save_file_path):
                    #    setting_fbytes = setting.get_file_bytes(version)
                    #    for dest_file, fbytes in setting_fbytes:
                    #        path = utils.path_join(extract_path, dest_file)
                    #        with open(path, 'wb+') as d:
                    #            d.write(fbytes)
                    #        self.progress_text += '.'

                    self.progress_text += '.'

            except (tarfile.ReadError, zipfile.BadZipfile) as e:
                if os.path.exists(save_file_path):
                    os.remove(save_file_path)
                self.extract_error = e
                self.logger.error(unicode(self.extract_error))
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
                shutil.copy(icon_path, icns_path)

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

    def make_output_dirs(self):
        self.output_err = ''
        try:
            self.progress_text = 'Removing old output directory...\n'

            output_dir = utils.path_join(self.output_dir(), self.project_name())
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir, ignore_errors=True)

            temp_dir = utils.path_join(TEMP_DIR, 'webexectemp')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            self.progress_text = 'Making new directories...\n'

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            os.makedirs(temp_dir)

            self.copy_files_to_project_folder()

            json_file = utils.path_join(self.project_dir(), 'package.json')

            global_json = utils.get_data_file_path('files/global.json')

            if self.output_package_json:
                with codecs.open(json_file, 'w+', encoding='utf-8') as f:
                    f.write(self.generate_json())


            with codecs.open(global_json, 'w+', encoding='utf-8') as f:
                f.write(self.generate_json(global_json=True))

            zip_file = utils.path_join(temp_dir, self.project_name()+'.nw')

            app_nw_folder = utils.path_join(temp_dir, self.project_name()+'.nwf')

            shutil.copytree(self.project_dir(), app_nw_folder,
                            ignore=shutil.ignore_patterns(output_dir))

            zip_files(zip_file, self.project_dir(), exclude_paths=[output_dir])
            for ex_setting in self.settings['export_settings'].values():
                if ex_setting.value:
                    self.progress_text = '\n'
                    name = ex_setting.display_name
                    self.progress_text = u'Making files for {}...'.format(name)
                    export_dest = utils.path_join(output_dir, ex_setting.name)
                    versions = re.findall('(\d+)\.(\d+)\.(\d+)', self.selected_version())[0]

                    minor = int(versions[1])
                    if minor >= 12:
                        export_dest = export_dest.replace('node-webkit', 'nwjs')

                    if os.path.exists(export_dest):
                        shutil.rmtree(export_dest, ignore_errors=True)

                    # shutil will make the directory for us
                    shutil.copytree(get_data_path('files/'+ex_setting.name),
                                    export_dest,
                                    ignore=shutil.ignore_patterns('place_holder.txt'))
                    shutil.rmtree(get_data_path('files/'+ex_setting.name), ignore_errors=True)
                    self.progress_text += '.'

                    if 'mac' in ex_setting.name:
                        uncomp_setting = self.get_setting('uncompressed_folder')
                        uncompressed = uncomp_setting.value
                        app_path = utils.path_join(export_dest,
                                                self.project_name()+'.app')

                        try:
                            shutil.move(utils.path_join(export_dest,
                                                     'nwjs.app'),
                                        app_path)
                        except IOError:
                            shutil.move(utils.path_join(export_dest,
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
                            shutil.copytree(app_nw_folder, app_nw_res)
                        else:
                            shutil.copy(zip_file, app_nw_res)
                        self.create_icns_for_app(utils.path_join(app_path,
                                                              'Contents',
                                                              'Resources',
                                                              'nw.icns'))

                        self.progress_text += '.'
                    else:
                        ext = ''
                        windows = False
                        if 'windows' in ex_setting.name:
                            ext = '.exe'
                            windows = True

                        nw_path = utils.path_join(export_dest,
                                               ex_setting.dest_files[0])

                        if windows:
                            self.replace_icon_in_exe(nw_path)

                        self.compress_nw(nw_path)

                        dest_binary_path = utils.path_join(export_dest,
                                                        self.project_name() +
                                                        ext)
                        if 'linux' in ex_setting.name:
                            self.make_desktop_file(dest_binary_path, export_dest)

                        join_files(dest_binary_path, nw_path, zip_file)

                        sevenfivefive = (stat.S_IRWXU |
                                         stat.S_IRGRP |
                                         stat.S_IXGRP |
                                         stat.S_IROTH |
                                         stat.S_IXOTH)
                        os.chmod(dest_binary_path, sevenfivefive)

                        self.progress_text += '.'

                        if os.path.exists(nw_path):
                            os.remove(nw_path)

        except Exception:
            exc = traceback.format_exception(sys.exc_info()[0],
                                             sys.exc_info()[1],
                                             sys.exc_info()[2])
            self.output_err += u''.join(exc)
            self.logger.error(exc)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def make_desktop_file(self, nw_path, export_dest):
        icon_set = self.get_setting('icon')
        icon_path = utils.path_join(self.project_dir(), icon_set.value)
        if os.path.exists(icon_path) and icon_set.value:
            shutil.copy(icon_path, export_dest)
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

        os.chmod(dfile_path, 0755)

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

        plat = platform.system()+platform.architecture()[0]
        upx_version = comp_dict.get(plat, None)

        if upx_version is not None:
            upx_bin = upx_version
            os.chmod(upx_bin, 0755)
            cmd = [upx_bin, '--lzma', u'-{}'.format(compression.value), unicode(nw_path)]
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
                            shutil.copy(setting.value, self.project_dir())
                            self.logger.info(u'Copying file {} to {}'.format(setting.value, self.project_dir()))
                        except shutil.Error as e:  # same file warning
                            self.logger.warning(u'Warning: {}'.format(e))
                        finally:
                            setting.value = os.path.basename(setting.value)

        os.chdir(old_dir)

    def convert_val_to_str(self, val):
        if isinstance(val, (list, tuple)):
            return ', '.join(val)
        return unicode(val).replace(self.project_dir()+os.path.sep, '')


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

            if ext == '.py':
                env_file = get_file('files/env_vars.py')
                env_contents = codecs.open(env_file, 'r', encoding='utf-8').read()
                env_vars = env_contents.format(proj_dir=self.project_dir(),
                                               proj_name=self.project_name(),
                                               export_dir=export_dir,
                                               export_dirs=str(export_dirs))
                pycontents = '{}\n{}'.format(env_vars, contents)

                command = ['python', '-c', pycontents]


            elif ext == '.bash':
                env_file = get_file('files/env_vars.bash')
                env_contents = codecs.open(env_file, 'r', encoding='utf-8').read()
                ex_dir_vars = ''

                for ex_dir in export_dirs:
                    ex_dir_vars += "'{}' ".format(ex_dir)

                env_vars = env_contents.format(proj_dir=self.project_dir(),
                                               proj_name=self.project_name(),
                                               export_dir=export_dir,
                                               export_dirs=ex_dir_vars)
                shcontents = '{}\n{}'.format(env_vars, contents)

                command = ['bash', '-c', shcontents]

            elif ext == '.bat':
                env_file = get_file('files/env_vars.bat')
                env_contents = codecs.open(env_file, 'r', encoding='utf-8').read()
                ex_dir_vars = ''
                export_dict = {'mac-x64_dir': '',
                               'mac-x32_dir': '',
                               'win-x64_dir': '',
                               'win-x32_dir': '',
                               'linux-x64_dir': '',
                               'linux-x32_dir': ''}

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

        versions = re.findall('v(\d+)\.(\d+)\.(\d+)', path)[0]

        minor = int(versions[1])
        if minor >= 12:
            path = path.replace('node-webkit', 'nwjs')

        url = path
        file_name = setting.save_file_path(self.selected_version(), location)
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
            url = urllib2.Request(url, headers=headers)

        web_file = urllib2.urlopen(url)
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
            for dest_file in ex_setting.dest_files:
                f_path = get_data_file_path('files/{}/{}'.format(ex_setting.name, dest_file))
                if os.path.exists(f_path):
                    os.remove(f_path)


class ArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: {}\n'.format(message))
        self.print_help()
        sys.exit(2)

def unicode_arg(bytestring):
    unicode_string = bytestring.decode(sys.getfilesystemencoding())
    return unicode_string

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
                    setting.description += u' Possible values: {{{}}}'.format(', '.join([unicode(x) for x in setting.values]))
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
        output_err = u''.join(traceback.format_exception(type_, value, tback))
        logger.error(u'{}'.format(output_err))
        sys.__excepthook__(type_, value, tback)

    sys.excepthook = my_excepthook

    command_base.logger = logger

    if args.quiet:
        command_base.quiet = True

    command_base._project_dir = args.project_dir
    command_base._output_dir = (args.output_dir or
                                utils.path_join(args.project_dir, 'output'))

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
