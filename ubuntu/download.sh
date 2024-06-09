#!/bin/bash

version="jammy"

# Download latest jammy lts cloud image
download_url="https://cloud-images.ubuntu.com/$version/current/$version-server-cloudimg-amd64-disk-kvm.img"

# Extract the filename from the URL
filename="$version-ubuntu-cloud.qcow2"

# Check if the file already exists in the current directory
if [ -e "$filename" ]; then
    echo "File $filename already exists. Skipping download."
else
    # Download the URL
    curl -o $filename "$download_url"
    echo "Download complete: $filename"
fi