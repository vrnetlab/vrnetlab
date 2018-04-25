#!/usr/bin/env python3

import re
import shutil

import requests
from bs4 import BeautifulSoup

base_url = "https://downloads.openwrt.org/"

def get_rel(url, version):
    res = requests.get(url)
    if not res.status_code == 200:
        return
    c = res.content
    soup = BeautifulSoup(c, "lxml")
    links = soup.find_all("a")
    for l in links:
        filename = l.string.strip()
        if not re.search('combined-ext4.img.gz', filename):
            #print("ignoring {}".format(filename))
            continue
        if re.search('[^0-9][0-9]{2}\.[0-9]{2}[^0-9]', filename):
            local_filename = filename
        else:
            local_filename = re.sub('^openwrt-', 'openwrt-{}-'.format(version), filename)
        file_url = "{}{}".format(url, filename)
        print("Downloading {} -> {}".format(file_url, local_filename))
        r = requests.get(file_url, stream=True)
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)


def main():
    res = requests.get("https://downloads.openwrt.org/")
    if not res.status_code == 200:
        return
    c = res.content
    soup = BeautifulSoup(c, "lxml")
    links = soup.find_all("a")
    for l in links:
        rel_url = "{}{}x86/kvm_guest/".format(base_url, l.attrs['href'])
        m = re.search('[^0-9]([0-9]{2}\.[0-9]{2})[^0-9]', l.attrs['href'])
        if not m:
            continue
        print(l.string.strip(), l.attrs['href'], rel_url)
        get_rel(rel_url, m.group(1))



main()
