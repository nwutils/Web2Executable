#!/usr/bin/python

import requests
import json
from pprint import pprint
from glob import glob

from semantic_version import Version
import getpass
import sys

def main():

    version = ""
    with open('files/version.txt') as f:
        version = f.read().strip()

    base_url = 'https://api.github.com/repos/jyapayne/Web2Executable/releases'

    req = requests.get(base_url+'/tags/'+version)

    update = False
    rel_id = None
    upload_url = None

    github_user = input('Github user:')

    password = getpass.getpass('Password:')

    if req.status_code == 200:
        print('Found release:', version)
        json_data = json.loads(req.text)
        tag = json_data.get('tag_name', '')
        cur_ver = Version(tag[1:-1])
        new_ver = Version(version[1:-1])
        if new_ver <= cur_ver:
            update = True
            rel_id = json_data['id']
            upload_url = json_data['upload_url'].replace('{?name,label}', '')

    if not update:
        print('Creating release:', version)
        data = {'tag_name': version,
                'target_commitish': 'master',
                'name': 'Web2Executable ' + version}
        post_res = requests.post(base_url, data=json.dumps(data), auth=(github_user, password))
        if post_res.status_code == 201:
            json_data = json.loads(post_res.text)
            upload_url = json_data['upload_url'].replace('{?name,label}', '')
            rel_id = json_data['id']
        else:
            print('Authentication failed!')

    if rel_id:
        zip_files = glob('*.zip')
        for zip_file in zip_files:
            with open(zip_file, 'rb') as zipf:
                file_data = zipf.read()
                print('Uploading file {}...'.format(zip_file))
                data = {'name': zip_file}
                headers = {'Content-Type': 'application/zip'}
                r = requests.post(upload_url, params=data, data=file_data, headers=headers, auth=(github_user, password))
                if r.status_code == 201:
                    print('Success!')
                else:
                    print('Error:', r.text)


if __name__ == '__main__':
    main()
