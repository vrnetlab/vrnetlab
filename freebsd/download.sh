#!/bin/bash

# Webpage with links to images
base_url="https://bsd-cloud-image.org"

# Download the webpage content
webpage_content=$(curl -s "$base_url")

# Find URLs that match the pattern "freebsd*zfs*.qcow2" and select the most recent version
download_url=$(echo "$webpage_content" | grep -oE 'https?://[^"]+freebsd[^"]+zfs[^"]+\.qcow2' | sort | tail -n 1)

# Extract the filename from the URL
filename=$(basename "$download_url")

# Check if the file already exists in the current directory
if [ -e "$filename" ]; then
    echo "File $filename already exists. Skipping download."
else
    # Download the URL
    curl -O "$download_url"
    echo "Download complete: $filename"
fi