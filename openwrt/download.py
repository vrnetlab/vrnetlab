#!/usr/bin/env python3
import os
import re
import requests
from lxml import html

def get_hrefs(url):
    'Fetch, parse, strip and return [href,href,..]'
    res = requests.get(url)
    if not res.status_code == 200:
        return
    tree = html.fromstring(res.content)
    anchors = tree.xpath('//a[@href]')
    refs = list(map(lambda a: a.get('href').strip('/'), anchors))
    return refs

def get_file(url, save_dest):
    'Fetch, write and return Content-Length'
    with requests.get(url, stream=True) as src:
        with open(save_dest, 'wb') as dest:
            dest.write(src.content)
            dest.close()
        src.close()
        return src.headers.get('Content-Length')

def get_latest(releases):
    'Find the latest NN out of many NN.nn.nn'
    release_matrix = {}
    for rel in releases:
        if not re.match('^\d{2}\.\d{2}\.\d+', rel):
            continue
        major = rel.split('.')[0]
        release_matrix.setdefault(major, '')
        release_matrix[major] = max(release_matrix[major], rel)
    return list(release_matrix.values())


def main():

    base_url = "https://downloads.openwrt.org/releases"
    stable_releases = get_hrefs(base_url)
    latest_releases = get_latest(stable_releases)

    for release in  latest_releases:

        base_x86_64= f'{base_url}/{release}/targets/x86/64'
        for filename in get_hrefs(base_x86_64):
            # ignore if not ext4 fs
            if not re.match('^openwrt-.*-combined-ext4.img.gz', filename) and \
               not re.match('^openwrt-.*-ext4-combined.img.gz', filename):
                continue

            remote_file = f'{base_x86_64}/{filename}'
            local_file = os.path.basename(remote_file)
            size = get_file(remote_file, local_file)
            print(f'Downloaded {local_file} ({size} bytes)')

main()
