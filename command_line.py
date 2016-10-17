"""Command-line module for Web2Executable

This module implements all of the functionality for Web2Executable that does
not require a GUI. This module can be run as a standalone script that will act
as a command-line interface for Web2Executable.

Run Example:
    Once the requirements have been installed and `SETUP.md`
    has been followed, execute

        $ python3.4 command_line.py --help

    for more information on all of the available options and usage
    instructions. A full example might be:

        $ python3.4 command_line.py --main index.html \
            --export-to=mac-x64 ~/Projects/MyProject/

"""

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
import plistlib
import codecs
import ssl
from datetime import datetime, timedelta

from io import StringIO

import config
import utils
from utils import zip_files, join_files
from utils import get_data_path, get_data_file_path
from util_classes import Setting

from image_utils.pycns import save_icns
from pepy.pe import PEFile

from semantic_version import Version

from configobj import ConfigObj

class CommandBase(object):
    """The common class for the CMD and the GUI"""
    def __init__(self, quiet=False):
        self.quiet = quiet
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
        self.logger = config.logger
        self.update_nw_versions(None)
        self.setup_nw_versions()

    def update_nw_versions(self, button):
        self.progress_text = 'Updating nw versions...'
        self.get_versions()
        self.progress_text = '\nDone.\n'

    def setup_nw_versions(self):
        """Get the nw versions stored in the local file"""
        nw_version = self.get_setting('nw_version')
        nw_version.values = []
        try:
            ver_file = get_data_file_path(config.VER_FILE)
            with codecs.open(ver_file, encoding='utf-8') as f:
                for line in f:
                    nw_version.values.append(line.strip())
        except IOError:
            nw_version.values.append(nw_version.default_value)

    def get_nw_versions(self):
        """Get the already downloaded nw versions from the settings"""
        nw_version = self.get_setting('nw_version')
        return nw_version.values[:]

    def get_settings(self):
        """Load all of the settings from the settings config file"""
        config_file = config.get_file(config.SETTINGS_FILE)

        contents = codecs.open(config_file, encoding='utf-8').read()

        contents = contents.replace('{DEFAULT_DOWNLOAD_PATH}',
                                    config.DEFAULT_DOWNLOAD_PATH)

        config_io = StringIO(contents)
        config_obj = ConfigObj(config_io, unrepr=True).dict()

        settings = {'setting_groups': []}
        setting_items = (list(config_obj['setting_groups'].items()) +
                         [('export_settings', config_obj['export_settings'])] +
                         [('compression', config_obj['compression'])])

        for setting_group, setting_group_dict in setting_items:
            settings[setting_group] = {}
            for setting_name, setting_dict in setting_group_dict.items():
                for key, val in setting_dict.items():
                    if '_callback' in key:
                        setting_dict[key] = getattr(self, setting_dict[key])
                setting_obj = Setting(name=setting_name, **setting_dict)
                settings[setting_group][setting_name] = setting_obj

        sgroup_items = config_obj['setting_groups'].items()
        for setting_group, setting_group_dict in sgroup_items:
            settings['setting_groups'].append(settings[setting_group])

        self._setting_items = (list(config_obj['setting_groups'].items()) +
                         [('export_settings', config_obj['export_settings'])] +
                         [('compression', config_obj['compression'])])

        config_obj.pop('setting_groups')
        config_obj.pop('export_settings')
        config_obj.pop('compression')

        self._setting_items += config_obj.items()

        for key, val in config_obj.items():
            settings[key] = val

        return settings

    def project_dir(self):
        """Get the stored project_dir"""
        return self._project_dir

    def output_dir(self):
        """Get the stored output_dir"""
        return self._output_dir

    def project_name(self):
        """Get the project name"""
        return (self._project_name or
                os.path.basename(os.path.abspath(self.project_dir())))

    def sub_output_pattern(self, pattern):
        """
        Substitute patterns for setting values
        """
        byte_pattern = bytearray(pattern.encode())

        val_dict = self.get_tag_value_dict()

        start = 0
        end = 0

        in_sub = False

        i = 0

        while i < len(byte_pattern):
            char = chr(byte_pattern[i])
            next_char = None
            if i != len(byte_pattern) - 1:
                next_char = chr(byte_pattern[i+1])

            if char == '%':
                if next_char == '(':
                    start = i
                    in_sub = True

            if in_sub:
                end = i

            if char == ')':
                in_sub = False
                old_string = str(byte_pattern[start:end+1], 'utf-8')
                sub = val_dict.get(old_string)

                if sub is not None:
                    sub = str(sub)
                    byte_pattern[start:end+1] = sub.encode()
                    i = i + (len(sub)-len(old_string))

            i += 1

        return str(byte_pattern, 'utf-8').replace('/', '_').replace('\\', '_')


    def get_tag_dict(self):
        """
        Gets the tag dictionary used to populate the
        auto completion of the output name pattern field

        Returns:
            A dict object containing the mapping between friendly names
            and setting names.
        """
        tag_dict = {}
        for setting_group in (self.settings['setting_groups'] +
                              [self.settings['export_settings']] +
                              [self.settings['compression']]):
            for key in setting_group.keys():
                setting = setting_group[key]
                tag_dict[setting.display_name] = '%('+key+')'

        return tag_dict

    def get_tag_value_dict(self):
        """
        Gets the tag to value dictionary to substitute values
        """
        tag_dict = {}
        for setting_group in (self.settings['setting_groups'] +
                              [self.settings['export_settings']] +
                              [self.settings['compression']]):
            for key in setting_group.keys():
                setting = setting_group[key]
                tag_dict['%('+key+')'] = setting.value

        return tag_dict

    def get_setting(self, name):
        """Get a setting by name

        Args:
            name: a string to search for

        Returns:
            A setting object or None
        """

        for setting_group in (self.settings['setting_groups'] +
                              [self.settings['export_settings']] +
                              [self.settings['compression']]):
            if name in setting_group:
                setting = setting_group[name]
                return setting

    def show_error(self, error):
        """Show an error using the logger"""
        if self.logger is not None:
            self.logger.error(error)

    def enable_ui_after_error(self):
        """
        Empty method for compatibility with the GUI superclass. DO NOT DELETE!
        """
        pass

    def get_default_nwjs_branch(self):
        """
        Get the default nwjs branch to search for
        the changelog from github.
        """
        query_api = False
        nwjs_branch_path = get_data_file_path(config.NW_BRANCH_FILE)

        if os.path.exists(nwjs_branch_path):
            mod_time = os.path.getmtime(nwjs_branch_path)
            mod_time = datetime.fromtimestamp(mod_time)
            hour_ago = datetime.now() - timedelta(hours=1)

            if mod_time <= hour_ago:
                query_api = True
        else:
            query_api = True

        branch = None

        if query_api:
            github_url = self.settings['version_info']['github_api_url']

            resp = utils.urlopen(github_url)
            json_string = resp.read().decode('utf-8')
            data = json.loads(json_string)
            branch = data['default_branch']

            with codecs.open(nwjs_branch_path, 'w', encoding='utf-8') as f:
                f.write(branch)

        else:
            with codecs.open(nwjs_branch_path, 'r', encoding='utf-8') as f:
                branch = f.read().strip()

        return branch

    def get_versions(self):
        """Get the versions from the NW.js Github changelog"""
        if self.logger is not None:
            self.logger.info('Getting versions...')

        union_versions = set()

        current_branch = self.get_default_nwjs_branch()

        for urlTuple in self.settings['version_info']['urls']:
            url, regex = urlTuple
            url = url.format(current_branch)
            response = utils.urlopen(url)
            html = response.read().decode('utf-8')

            nw_version = self.get_setting('nw_version')

            old_versions = set(nw_version.values)
            old_versions = old_versions.union(union_versions)
            new_versions = set(re.findall(regex, html))

            union_versions = old_versions.union(new_versions)

        versions = sorted(union_versions,
                          key=Version, reverse=True)

        filtered_vers = []

        for v in versions:
            ver = Version(v)
            if ver.major > 0 or (ver.major == 0 and ver.minor >= 13):
                filtered_vers.append(v)

        versions = filtered_vers

        nw_version.values = versions
        f = None
        try:
            ver_path = get_data_file_path(config.VER_FILE)
            with codecs.open(ver_path, 'w', encoding='utf-8') as f:
                for v in nw_version.values:
                    f.write(v+os.linesep)
        except IOError:
            exc_format = utils.format_exc_info(sys.exc_info)
            self.show_error(error)
            self.enable_ui_after_error()
        finally:
            if f:
                f.close()

    def download_file_with_error_handling(self):
        """
        Try to download a file and safely handle errors by showing them
        in the GUI.
        """
        setting = self.files_to_download.pop()
        location = self.get_setting('download_dir').value
        version = self.selected_version()
        path = setting.url.format(version, version)

        sdk_build_setting = self.get_setting('sdk_build')
        sdk_build = sdk_build_setting.value

        if sdk_build:
            path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

        try:
            return self.download_file(setting.url.format(version, version),
                                      setting)
        except (Exception, KeyboardInterrupt):
            if os.path.exists(setting.save_file_path(version, location)):
                os.remove(setting.save_file_path(version, location))

            exc_format = utils.format_exc_info(sys.exc_info)
            self.show_error(error)
            self.enable_ui_after_error()

    def load_package_json(self, json_path=None):
        """Load the package.json in the project or from json_path

        Args:
            json_path: the path to a custom json file with web2exe settings
        """
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
                self.progress_text = '{}\n'.format(e)
        return setting_list

    def process_app_settings(self, dic):
        """Process the app settings into the dic"""
        for setting_name, setting in self.settings['app_settings'].items():

            if setting.value is not None and setting.value != '':
                dic[setting_name] = setting.value
                if setting_name == 'keywords':
                    dic[setting_name] = re.findall('\w+', setting.value)
            else:
                dic.pop(setting_name, '')

    def process_window_settings(self, dic):
        """Process the window settings into the dic"""
        for setting_name, setting in self.settings['window_settings'].items():
            if setting.value is not None and setting.value != '':
                if setting.type == 'int':
                    try:
                        dic['window'][setting_name] = int(setting.value)
                    except ValueError:
                        pass
                else:
                    dic['window'][setting_name] = setting.value
            else:
                dic['window'].pop(setting_name, '')

    def process_webkit_settings(self, dic):
        """Process the webkit settings into the dic"""
        for setting_name, setting in self.settings['webkit_settings'].items():
            if setting.value is not None and setting.value != '':
                dic['webkit'][setting_name] = setting.value
            else:
                dic['webkit'].pop(setting_name, '')

    def process_webexe_settings(self, dic, global_json):
        """Set the web2exe settings based on remaining options
        Args:
            dic: a dict-like object representing the to be saved options
            global_json: a boolean telling whether to load global json options
        """
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


    def generate_json(self, global_json=False):
        """Generates the json config files for the exported app"""
        self.logger.info('Generating package.json...')

        dic = {'webexe_settings': {}}

        if not global_json:
            dic.update({'webkit': {}, 'window': {}})
            dic.update(self.original_packagejson)

            self.process_app_settings(dic)
            self.process_window_settings(dic)
            self.process_webkit_settings(dic)

        self.process_webexe_settings(dic, global_json)

        s = json.dumps(dic, indent=4)

        return s

    @property
    def extract_error(self):
        """Get the current extract error"""
        return self._extract_error

    @extract_error.setter
    def extract_error(self, value):
        """Write the extract error to the terminal"""
        if value is not None and not self.quiet:
            self._extract_error = value
            sys.stderr.write('\r{}'.format(self._extract_error))
            sys.stderr.flush()

    @property
    def output_err(self):
        """Get the current error"""
        return self._output_err

    @output_err.setter
    def output_err(self, value):
        """Write an error to the terminal"""
        if value is not None and not self.quiet:
            self._output_err = value
            sys.stderr.write('\r{}'.format(self._output_err))
            sys.stderr.flush()

    @property
    def progress_text(self):
        """Get the progress text currently set"""
        return self._progress_text

    @progress_text.setter
    def progress_text(self, value):
        """Write progress text to the terminal

        Args:
            value: The value to write to the terminal
        """
        if value is not None and not self.quiet:
            self._progress_text = value
            sys.stdout.write('\r{}'.format(self._progress_text))
            sys.stdout.flush()

    def load_from_json(self, json_str):
        """Load settings from the supplied json string

        Args:
            json_str: the json string to parse all of the GUI options from

        Returns:
            A list of Setting objects
        """
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
                            setting.type == 'folder' or
                            setting.type == 'int'):
                        val_str = self.convert_val_to_str(new_dic[item])
                        setting.value = val_str
                    if setting.type == 'strings':
                        ditem = new_dic[item]
                        strs = self.convert_val_to_str(ditem).split(',')
                        strs = [x.strip() for x in strs if x]
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
        """Get the currently selected version from the NW.js dropdown"""
        return self.get_setting('nw_version').value

    def extract_files(self):
        """Extract nw.js files to the specific version path"""
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
        """
        Converts the project icon to ICNS format and saves it
        to the path specified

        Args:
            icns_path: The path to write the icns file to
        """
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
        """Modifies the nw.js executable to have the project icon

        Args:
            exe_path: The path to write the new exe to
        """
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
        """Collects filled options and writes corresponding json files"""
        json_file = utils.path_join(self.project_dir(), 'package.json')

        global_json = utils.get_data_file_path(config.GLOBAL_JSON_FILE)

        # Write package json
        if self.output_package_json:
            with codecs.open(json_file, 'w+', encoding='utf-8') as f:
                f.write(self.generate_json())

        # Write global settings that are kept when installing new
        # versions
        with codecs.open(global_json, 'w+', encoding='utf-8') as f:
            f.write(self.generate_json(global_json=True))

    def clean_dirs(self, *dirs):
        """
        Delete directory trees with :py:func:`utils.rmtree` and recreate
        them

        Args:
            *dirs: directories to be cleaned
        """
        for directory in dirs:
            if os.path.exists(directory):
                utils.rmtree(directory, onerror=self.remove_readonly)
            if not os.path.exists(directory):
                os.makedirs(directory)

    def get_export_dest(self, ex_setting, output_dir):
        """Get the export destination path using the export setting

        Args:
            ex_setting: an export setting (eg: mac-x64)
            output_dir: the path of the output project directory

        Returns:
            A path to store the output files
        """
        export_dest = utils.path_join(output_dir, ex_setting.name)

        return export_dest

    def copy_export_files(self, ex_setting, export_dest):
        """Copy the export files to the destination path

        Args:
            ex_setting: an export setting (eg: mac-x64)
            export_dest: the path returned by get_export_dest()
        """

        if os.path.exists(export_dest):
            utils.rmtree(export_dest)

        # shutil will make the directory for us
        utils.copytree(get_data_path('files/'+ex_setting.name),
                       export_dest,
                        ignore=shutil.ignore_patterns('place_holder.txt'))
        utils.rmtree(get_data_path('files/'+ex_setting.name))

    def replace_localized_app_name(self, app_path):
        """
        Replace app name in InfoPlist.strings to make
        the app name appear in Finder

        Args:
            app_path: The exported application path
        """
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
        """Replaces the Info.plist file with the project settings
        contents

        Args:
            app_path: The exported application path
        """

        plist_path = utils.path_join(app_path, 'Contents', 'Info.plist')

        plist_dict = plistlib.readPlist(plist_path)

        plist_dict['CFBundleDisplayName'] = self.project_name()
        plist_dict['CFBundleName'] = self.project_name()
        version_setting = self.get_setting('version')
        plist_dict['CFBundleShortVersionString'] = version_setting.value
        plist_dict['CFBundleVersion'] = version_setting.value

        plistlib.writePlist(plist_dict, plist_path)

    def process_mac_setting(self, app_loc, export_dest,
                            ex_setting, uncompressed):
        """Process the Mac settings

        Args:
            app_loc: the app's location
            export_dest: the destination to export the app to
            uncompressed: boolean -> app is compressed or not
        """

        app_path = utils.path_join(export_dest,
                                   self.project_name()+'.app')

        nw_path = utils.path_join(export_dest, 'nwjs.app')
        self.compress_nw(nw_path, ex_setting)
        utils.move(nw_path, app_path)

        self.replace_plist(app_path)

        resource_path = utils.path_join(
            app_path,
            'Contents',
            'Resources'
        )

        app_nw_res = utils.path_join(resource_path, 'app.nw')

        if uncompressed:
            utils.copytree(app_loc, app_nw_res)
        else:
            utils.copy(app_loc, app_nw_res)

        self.progress_text += '.'

        self.create_icns_for_app(utils.path_join(resource_path,
                                                 'app.icns'))
        self.create_icns_for_app(utils.path_join(resource_path,
                                                 'document.icns'))
        self.replace_localized_app_name(app_path)

        self.progress_text += '.'


    def process_win_linux_setting(self, app_loc, export_dest,
                                  ex_setting, uncompressed):
        """Processes windows and linux settings

        Creates executable, modifies exe icon, and copies to the destination

        Args:
            app_loc: the location of the app
            export_dest: directory to copy app to
            ex_setting: the export setting (eg: mac-x32)
            uncompressed: boolean -> app is compressed or not

        """

        nw_path = utils.path_join(export_dest,
                                  ex_setting.binary_location)

        ext = ''
        if 'windows' in ex_setting.name:
            ext = '.exe'
            self.replace_icon_in_exe(nw_path)

        self.compress_nw(nw_path, ex_setting)

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



    def process_export_setting(self, ex_setting, output_dir,
                               temp_dir, app_loc, uncompressed):
        """Create the executable based on the export setting"""
        if ex_setting.value:
            self.progress_text = '\n'

            name = ex_setting.display_name

            self.progress_text = 'Making files for {}...'.format(name)

            export_dest = self.get_export_dest(ex_setting, output_dir)

            self.copy_export_files(ex_setting, export_dest)

            self.progress_text += '.'

            if 'mac' in ex_setting.name:
                self.process_mac_setting(app_loc, export_dest, ex_setting,
                                         uncompressed)
            else:
                self.process_win_linux_setting(app_loc, export_dest,
                                               ex_setting, uncompressed)


    def make_output_dirs(self, write_json=True):
        """Create the output directories for the application to be copied"""

        output_name = self.sub_pattern() or self.project_name()

        output_dir = utils.path_join(self.output_dir(), output_name)
        temp_dir = utils.path_join(config.TEMP_DIR, 'webexectemp')

        self.progress_text = 'Making new directories...\n'

        self.clean_dirs(temp_dir, output_dir)

        self.copy_files_to_project_folder()

        if write_json:
            self.write_package_json()

        app_loc = self.get_app_nw_loc(temp_dir, output_dir)

        uncomp_setting = self.get_setting('uncompressed_folder')
        uncompressed = uncomp_setting.value

        for ex_setting in self.settings['export_settings'].values():
            self.process_export_setting(ex_setting, output_dir, temp_dir,
                                        app_loc, uncompressed)

    def sub_pattern(self):
        """Returns the output pattern substitution or an empty string"""
        setting = self.get_setting('output_pattern')
        return self.sub_output_pattern(setting.value)

    def try_make_output_dirs(self):
        """Try to create the output directories if they don't exist"""
        self.output_err = ''
        try:
            self.make_output_dirs()
        except Exception:
            exc_format = utils.format_exc_info(sys.exc_info)
            self.logger.error(error)
            self.output_err += error
        finally:
            temp_dir = utils.path_join(config.TEMP_DIR, 'webexectemp')
            utils.rmtree(temp_dir, onerror=self.remove_readonly)

    def get_app_nw_loc(self, temp_dir, output_dir):
        """Copy the temporary app to the output_dir"""
        app_file = utils.path_join(temp_dir, self.project_name()+'.nw')

        uncomp_setting = self.get_setting('uncompressed_folder')
        uncompressed = uncomp_setting.value

        if uncompressed:
            app_nw_folder = utils.path_join(temp_dir,
                                            self.project_name()+'.nwf')

            utils.copytree(self.project_dir(), app_nw_folder,
                           ignore=shutil.ignore_patterns(output_dir))
            return app_nw_folder
        else:
            zip_files(app_file, self.project_dir(), exclude_paths=[output_dir])
            return app_file

    def get_version_tuple(self):
        """Get the currently selected version's tuple of major, minor, release

        Returns:
            A 3-tuple of (major, minor, release)
        """
        try:
            strs = re.findall('(\d+)\.(\d+)\.(\d+)',
                              self.selected_version())[0]
        except IndexError:
            strs = ['0','0','0']
        return [int(s) for s in strs]

    def copy_executable(self, export_path, dest_path,
                        nw_path, app_loc, uncompressed):
        """
        Merge the zip file into the exe and copy it to the destination path
        """
        package_loc = utils.path_join(export_path, 'package.nw')
        if uncompressed:
            utils.copytree(app_loc, package_loc)
            utils.copy(nw_path, dest_path)
        else:
            join_files(dest_path, nw_path, app_loc)


    def set_executable(self, path):
        """Modify the path to be executable by the OS"""
        sevenfivefive = (stat.S_IRWXU |
                         stat.S_IRGRP |
                         stat.S_IXGRP |
                         stat.S_IROTH |
                         stat.S_IXOTH)
        os.chmod(path, sevenfivefive)

    def make_desktop_file(self, nw_path, export_dest):
        """Make the linux desktop file for unity or other launchers"""

        icon_set = self.get_setting('icon')
        icon_path = utils.path_join(self.project_dir(), icon_set.value)

        if os.path.exists(icon_path) and icon_set.value:
            utils.copy(icon_path, export_dest)
            icon_path = utils.path_join(export_dest,
                                        os.path.basename(icon_path))
        else:
            icon_path = ''

        name = self.project_name()
        pdir = self.project_dir()

        version = self.get_setting('version')
        desc = self.get_setting('description')

        dfile_path = utils.path_join(export_dest, '{}.desktop'.format(name))

        file_str = (
            '[Desktop Entry]\n'
            'Version={}\n'
            'Name={}\n'
            'Comment={}\n'
            'Exec={}\n'
            'Icon={}\n'
            'Terminal=false\n'
            'Type=Application\n'
            'Categories=Utility;Application;\n'
        )

        file_str = file_str.format(
            version.value,
            name,
            desc.value,
            nw_path,
            icon_path
        )

        with codecs.open(dfile_path, 'w+', encoding='utf-8') as f:
            f.write(file_str)

        os.chmod(dfile_path, 0o755)

    def compress_nw(self, nw_path, ex_setting):
        """Compress the nw file using upx"""
        compression = self.get_setting('nw_compression_level')

        if compression.value == 0:
            return

        comp_dict = {
            'Darwin64bit': config.get_file(config.UPX_MAC_PATH),
            'Darwin32bit': config.get_file(config.UPX_MAC_PATH),
            'Linux64bit':  config.get_file(config.UPX_LIN64_PATH),
            'Linux32bit':  config.get_file(config.UPX_LIN32_PATH),
            'Windows64bit':  config.get_file(config.UPX_WIN_PATH),
            'Windows32bit':  config.get_file(config.UPX_WIN_PATH)
        }

        if config.is_installed():
            comp_dict['Windows64bit'] = get_data_file_path(config.UPX_WIN_PATH)
            comp_dict['Windows32bit'] = get_data_file_path(config.UPX_WIN_PATH)

        plat = platform.system()+platform.architecture()[0]
        upx_version = comp_dict.get(plat, None)

        if upx_version is not None:
            upx_bin = upx_version
            os.chmod(upx_bin, 0o755)

            cmd = [upx_bin, '--lzma', '-{}'.format(compression.value)]

            if 'windows' in ex_setting.name:
                path = os.path.join(os.path.dirname(nw_path), '*.dll')
                cmd.extend(glob.glob(path))
            elif 'linux' in ex_setting.name:
                path = os.path.join(os.path.dirname(nw_path), 'lib', '*.so')
                cmd.extend(glob.glob(path))
            elif 'mac' in ex_setting.name:
                dylib_path = utils.path_join(
                    nw_path,
                    'Contents',
                    'Versions',
                    '**',
                    'nwjs Framework.framework',
                )
                framework_path = os.path.join(dylib_path, 'nwjs Framework')
                cmd.extend(glob.glob(framework_path))
                path = os.path.join(dylib_path, '*.dylib')
                cmd.extend(glob.glob(path))

            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    startupinfo=startupinfo
                )
            else:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE
                )

            self.progress_text = '\n\n'
            self.progress_text = 'Compressing files'

            while proc.poll() is None:
                self.progress_text += '.'
                time.sleep(2)

            output, err = proc.communicate()
            if err:
                args = ex_setting.name, platform.system(), ex_setting.name
                self.output_err = ('Cannot compress files for {} on {}!\n'
                                   'Run Web2Exe on {} to '
                                   'compress successfully.').format(*args)

    def remove_readonly(self, action, name, exc):
        """Try to remove readonly files"""
        try:
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
        except Exception as e:
            error = 'Failed to remove file: {}.'.format(name)
            error += '\nError recieved: {}'.format(e)
            self.logger.error(error)
            self.output_err += error

    def copy_files_to_project_folder(self):
        """
        Copy external files to the project folder
        so that they are bundled with the exe
        """
        old_dir = config.CWD

        os.chdir(self.project_dir())
        self.logger.info('Copying files to {}'.format(self.project_dir()))

        for sgroup in self.settings['setting_groups']:
            for setting in sgroup.values():
                if setting.copy and setting.type == 'file' and setting.value:
                    f_path = setting.value.replace(self.project_dir(), '')
                    if os.path.isabs(f_path):
                        message = ('Copying file {} '
                                   'to {}'.format(setting.value,
                                                  self.project_dir()))
                        try:
                            utils.copy(setting.value, self.project_dir())
                            self.logger.info(message)
                        except shutil.Error as e:  # same file warning
                            self.logger.warning('Warning: {}'.format(e))
                        finally:
                            setting.value = os.path.basename(setting.value)

        os.chdir(old_dir)

    def convert_val_to_str(self, val):
        """Convert a setting value to a string path"""
        if isinstance(val, (list, tuple)):
            return ', '.join(val)
        return str(val).replace(self.project_dir()+os.path.sep, '')

    def get_python_command(self, export_dict, export_dir,
                           export_dirs, contents):
        """
        Inject arguments into python script and then execute it in a temp
        directory.
        """
        export_opts = self.get_export_options()
        env_file = config.get_file(config.ENV_VARS_PY_PATH)
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

        return command

    def get_bat_command(self, export_dict, export_dir, export_dirs, contents):
        """
        Inject arguments into bat script and then execute it in a temp
        directory.
        """
        export_opts = self.get_export_options()
        env_file = config.get_file(config.ENV_VARS_BAT_PATH)
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

        bat_file = utils.path_join(config.TEMP_DIR,
                                   '{}.bat'.format(self.project_name()))

        self.logger.debug(batcontents)

        with open(bat_file, 'w+') as f:
            f.write(batcontents)

        command = [bat_file]

        return command

    def get_bash_command(self, export_dict, export_dir, export_dirs, contents):
        """
        Inject arguments into bash script and then execute it in a temp
        directory.
        """
        export_opts = self.get_export_options()
        env_file = config.get_file(config.ENV_VARS_BASH_PATH)
        env_contents = codecs.open(env_file, 'r', encoding='utf-8').read()
        ex_dir_vars = ''

        for i, ex_dir in enumerate(export_dirs):
            opt = export_opts[i]
            export_dict[opt+'_dir'] = ex_dir
            ex_dir_vars += ex_dir
            if i != (len(export_dirs)-1):
                ex_dir_vars += ' '

        env_vars = env_contents.format(proj_dir=self.project_dir(),
                                       proj_name=self.project_name(),
                                       export_dir=export_dir,
                                       num_dirs=len(export_dirs),
                                       export_dirs=ex_dir_vars,
                                       **export_dict)
        bashcontents = '{}\n{}'.format(env_vars, contents)

        bash_file = utils.path_join(config.TEMP_DIR,
                                    '{}.bash'.format(self.project_name()))

        self.logger.debug(bashcontents)

        with open(bash_file, 'w+') as f:
            f.write(bashcontents)

        command = [bash_file]

        return command

    def run_script(self, script):
        """Run a script specified in the GUI after exporting

        Args:
            script: the path of the script to be ran
        """

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
                export_dirs.append('{}{}{}'.format(export_dir,
                                                   os.path.sep,
                                                   opt))

            command = None
            bat_file = None

            export_dict = {'mac-x64_dir': '',
                           'mac-x32_dir': '',
                           'windows-x64_dir': '',
                           'windows-x32_dir': '',
                           'linux-x64_dir': '',
                           'linux-x32_dir': ''}

            if ext == '.py':
                command = self.get_python_command(export_dict, export_dir,
                                                  export_dirs, contents)
            elif ext == '.bash':
                command = self.get_bash_command(export_dict, export_dir,
                                                export_dirs, contents)
            elif ext == '.bat':
                command = self.get_bat_command(export_dict, export_dir,
                                               export_dirs, contents)

            proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            output, error = proc.communicate()
            output = output.strip()
            error = error.strip()

            if bat_file:
                os.remove(bat_file)

            with open(config.get_file('script-output.txt'), 'w+') as f:
                f.write('Output:\n{}'.format(output))
                if error:
                    f.write('\n\nErrors:\n{}\n'.format(error))

            self.progress_text = 'Done executing script.'
        else:
            self.progress_text = ('\nThe script {} does not exist. '
                                  'Not running.'.format(script))


    def export(self, write_json=True):
        """Start the exporting process

        Kwargs:
            write_json: boolean -> write json output or not
        """
        self.get_files_to_download()
        res = self.try_to_download_files()
        if res:
            self.make_output_dirs(write_json)
            script = self.get_setting('custom_script').value
            self.run_script(script)
            self.progress_text = '\nDone!\n'
            out_dir = '{}{}{}'.format(self.output_dir(),
                                      os.path.sep,
                                      self.project_name())
            self.progress_text = 'Output directory is {}.\n'.format(out_dir)
            self.delete_files()

    def get_export_options(self):
        """Get all of the export options selected"""
        options = []
        for setting_name, setting in self.settings['export_settings'].items():
            if setting.value is True:
                options.append(setting_name)
        return options

    def get_files_to_download(self):
        """Get all the files needed for download based on export settings"""
        self.files_to_download = []
        for setting_name, setting in self.settings['export_settings'].items():
            if setting.value is True:
                self.files_to_download.append(setting)
        return True

    def try_to_download_files(self):
        if self.files_to_download:
            return self.download_file_with_error_handling()

    def continue_downloading_or_extract(self):
        """If there are more files to download, continue; otherwise extract"""
        if self.files_to_download:
            return self.download_file_with_error_handling()
        else:
            self.progress_text = 'Extracting files.'
            return self.extract_files()

    def download_file(self, path, setting):
        """Download a file from the path and setting"""
        self.logger.info('Downloading file {}.'.format(path))

        location = self.get_setting('download_dir').value

        sdk_build_setting = self.get_setting('sdk_build')
        sdk_build = sdk_build_setting.value

        if sdk_build:
            path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

        url = path

        file_name = setting.save_file_path(self.selected_version(),
                                           location, sdk_build)

        tmp_file = list(os.path.split(file_name))
        tmp_file[-1] = '.tmp.' + tmp_file[-1]
        tmp_file = os.sep.join(tmp_file)
        tmp_size = 0

        archive_exists = os.path.exists(file_name)
        tmp_exists = os.path.exists(tmp_file)

        dest_files_exist = False

        forced = self.get_setting('force_download').value

        if (archive_exists or dest_files_exist) and not forced:
            self.logger.info('File {} already downloaded. '
                             'Continuing...'.format(path))
            return self.continue_downloading_or_extract()
        elif tmp_exists and (os.stat(tmp_file).st_size > 0):
            tmp_size = os.stat(tmp_file).st_size
            headers = {'Range': 'bytes={}-'.format(tmp_size)}
            url = request.Request(url, headers=headers)

        web_file = utils.urlopen(url)

        f = open(tmp_file, 'ab')

        meta = web_file.info()
        file_size = tmp_size + int(meta.get_all("Content-Length")[0])

        version = self.selected_version()
        version_file = self.settings['base_url'].format(version)

        short_name = path.replace(version_file, '')

        MB = file_size/1000000.0

        downloaded = ''

        if tmp_size:
            self.progress_text = 'Resuming previous download...\n'
            size = tmp_size/1000000.0
            self.progress_text = 'Already downloaded {:.2f} MB\n'.format(size)

        self.progress_text = ('Downloading: {}, '
                              'Size: {:.2f} MB {}\n'.format(short_name,
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
            is_dir = os.path.isdir(file_name)
            if sys.platform.startswith('win32') and not is_dir:
                os.remove(file_name)
                os.rename(tmp_file, file_name)
            else:
                os.remove(tmp_file)
                raise OSError

        return self.continue_downloading_or_extract()

    def delete_files(self):
        """Delete files left over in the data path from downloading"""
        for ex_setting in self.settings['export_settings'].values():
            f_path = get_data_file_path('files/{}/'.format(ex_setting.name))
            if os.path.exists(f_path):
                utils.rmtree(f_path)


class ArgParser(argparse.ArgumentParser):
    """Custom argparser that prints help if there is an error"""
    def error(self, message):
        sys.stderr.write('error: {}\n'.format(message))
        self.print_help()
        sys.exit(2)

def get_arguments(command_base):
    """Retrieves arguments from the command line"""

    parser = ArgParser(description=('Command line interface '
                                    'to web2exe. '
                                    '{}'.format(config.__version__)),
                                     prog='web2execmd')

    parser.add_argument('project_dir', metavar='project_dir',
                        help='The project directory.')
    parser.add_argument('--output-dir', dest='output_dir',
                        help='The output directory for exports.')
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
    parser.add_argument('--cmd-version', action='version',
                        version='%(prog)s {}'.format(config.__version__))

    generate_setting_args(command_base, parser)

    export_args = [arg for arg in command_base.settings['export_settings']]
    parser.add_argument('--export-to', dest='export_options',
                        nargs='+', required=True,
                        choices=export_args,
                        help=('Choose at least one system '
                              'to export to.'))

    return parser.parse_args()

def generate_setting_args(command_base, parser):
    """
    Generate arguments based on the contents of settings.cfg

    Args:
        command_base (CommandBase): An instance of the CommandBase class
                                    that has been initialized
        parser (ArgParser): An instance of the ArgParser class that will hold
                            the generated arguments
    """
    setting_dicts = (command_base.settings['setting_groups'] +
                     [command_base.settings['compression']])
    for setting_group_dict in setting_dicts:
        for setting_name, setting in setting_group_dict.items():
            kwargs = {}

            # Set the default values and required values
            # Special case when handling project name
            if setting_name == 'name':
                kwargs.update({'default': command_base.project_name})
            else:
                kwargs.update({'required': setting.required,
                               'default': setting.default_value})
            action = 'store'
            option_name = setting_name.replace('_', '-')

            if isinstance(setting.default_value, bool):
                action = ('store_true' if setting.default_value is False
                          else 'store_false')
                kwargs.update({'action': action})
                if setting.default_value is True:
                    option_name = 'disable-{}'.format(option_name)
            else:
                if setting.values:
                    kwargs.update({'choices': setting.values})
                    possible_vals = ', '.join([str(x) for x in setting.values])
                    val_desc = ' Possible values: {{{}}}'.format(possible_vals)
                    setting.description += val_desc
                    kwargs.update({'metavar': ''})
                else:
                    kwargs.update({'metavar':
                                        '<{}>'.format(setting.display_name)})

            parser.add_argument(
                '--{}'.format(option_name),
                dest=setting_name,
                # Ignore any percent signs in the description.
                help=setting.description.replace('%', '%%'),
                **kwargs
            )

def setup_logging(args, command_base):
    """Setup debug logging for CMD"""
    import logging
    import logging.handlers as lh

    if args.verbose:
        logging.basicConfig(
            stream=sys.stdout,
            format=("%(levelname) -10s %(module)s.py: "
                    "%(lineno)s %(funcName)s - %(message)s"),
            level=logging.DEBUG
        )
    else:
        # Log to the logfile in config.py
        logging.basicConfig(
            filename=config.LOG_FILENAME,
            format=("%(levelname) -10s %(asctime)s %(module)s.py: "
                    "%(lineno)s %(funcName)s - %(message)s"),
            level=logging.DEBUG
        )

    config.logger = logging.getLogger('CMD Logger')
    config.handler = lh.RotatingFileHandler(config.LOG_FILENAME,
                                            maxBytes=100000,
                                            backupCount=2)
    config.logger.addHandler(config.handler)

    def my_excepthook(type_, value, tback):
        exc_format = traceback.format_exception(type_, value, tback)
        output_err = ''.join([x for x in exc_format])
        config.logger.error('{}'.format(output_err))
        sys.__excepthook__(type_, value, tback)

    sys.excepthook = my_excepthook

    command_base.logger = config.logger

    if args.quiet:
        command_base.quiet = True

def setup_project_name(args, command_base):
    """Set the project name and app name from args"""
    if args.app_name is None:
        args.app_name = command_base.project_name()

    if args.name is not None:
        setting = command_base.get_setting('name')
        args.name = setting.filter_name(args.name if not callable(args.name)
                                        else args.name())

    command_base._project_name = (args.app_name if not callable(args.app_name)
                                  else args.app_name())

    if not args.title:
        args.title = command_base.project_name()

    if not args.id:
        args.id = command_base.project_name()

def setup_directories(args, command_base):
    """Setup the project and output directories from args"""
    command_base._project_dir = args.project_dir

    command_base._output_dir = (args.output_dir or
                                utils.path_join(command_base._project_dir,
                                                'output'))

def read_package_json_file(args, command_base):
    """Either load project json or load custom json from file"""
    if args.load_json is True:
        command_base.load_package_json()
    elif args.load_json:
        # Load json is a path, so load JSON from the specified file
        command_base.load_package_json(args.load_json)

def write_package_json_file(args, command_base):
    """Determine whether or not to write the package json file."""
    write_json = False

    if args.load_json is not True and args.load_json:
        # Load json is a path, so check if the default package json
        # exists before writing it. If it exists, don't overwrite it
        # so that people's changes to the file are preserved
        project_dir = command_base.project_dir()
        json_path = os.path.abspath(os.path.expanduser(args.load_json))
        left_over_path = json_path.replace(project_dir, '')

        # Write package.json if it's not already in the root
        # of the project
        if left_over_path != 'package.json':
            write_json = True

    command_base.export(write_json)

def initialize_setting_values(args, command_base):
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

def main():
    """Main setup and argument parsing"""
    command_base = CommandBase()
    command_base.init()

    args = get_arguments(command_base)

    setup_logging(args, command_base)
    setup_directories(args, command_base)
    setup_project_name(args, command_base)

    initialize_setting_values(args, command_base)

    read_package_json_file(args, command_base)
    write_package_json_file(args, command_base)

if __name__ == '__main__':
    main()
