#!/usr/bin/env python3

import re
import shutil
import sys
import os
import gzip

import requests
from bs4 import BeautifulSoup, Tag

base_url = "https://downloads.openwrt.org/"

def get_rel(url, version):
    res = requests.get(url)
    if not res.status_code == 200:
        return
    c = res.content
    soup = BeautifulSoup(c, "lxml")
    links = soup.find_all("a")
    for l in links:
        #print(l)
        
        #filename = l.string.strip()
        filename = l['href']
        if not (re.search('combined-ext4.img.gz', filename) or re.search('generic-ext4-combined.img.gz', filename)):
            #print("ignoring {}".format(filename))
            continue
        if re.search('^openwrt-x86-', filename):
            local_filename = re.sub('^openwrt-x86-', 'openwrt-{}-x86-'.format(version), filename)
        file_url = "{}{}".format(url, filename)
        if not os.path.exists(filename):
            print("Downloading {} -> {}".format(file_url, filename))
            r = requests.get(file_url, stream=True)
            print(filename)
            base_name, file_extension = os.path.splitext(filename)
            if file_extension == ".gz":
                output_file = base_name
            print(output_file)
            with open(filename, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            try:
                with gzip.open(filename, 'rb') as f_in:
                    with open(output_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                print(f"The file was successfully unpacked: {output_file}")
            except gzip.BadGzipFile:
                if not os.path.exists(output_file):
                    print(f"Warning: The file '{filename}' is not a valid GZIP file and could not be unpacked.")
                else:
                    print(f"gzip: {filename}: decompression OK, trailing garbage ignored. ")
            except Exception as e:
                print(f"Error unpacking the file '{filename}': {e}")
        else:
            print("File '{}' already exists. Skipping download.".format(filename))


def main():
    res = requests.get("https://downloads.openwrt.org/")
    if not res.status_code == 200:
        return
    c = res.content
    soup = BeautifulSoup(c, "lxml")
    links = soup.find_all("a")
    for l in links:
        m = re.search('\/\/', l.attrs['href'])
        if not m:
            rel_url = "{}{}x86/64/".format(base_url, l.attrs['href'])
        else:
            current_href = l['href']
            new_href = 'https:' + current_href
            l['href'] = new_href
            rel_url = "{}x86/64/".format(l.attrs['href'])
        m = re.search('[^0-9]([0-9]{2}\.[0-9]{2}[^0-9](?:[0-9]{1,2}))|[^0-9]([0-9]{2}\.[0-9]{2})', l.attrs['href'])
        if not m:
            continue
        #print(l.string.strip(), l.attrs['href'], rel_url)
        get_rel(rel_url, m.group(1))



main()
