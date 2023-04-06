VENDOR=Nokia
NAME=VSR
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

## Configure proxy support here for the build process.
## Uncomment and complete the following lines as appropriate.
#http_proxy=http://192.168.1.1:3128
#https_proxy=http://192.168.1.1:3128

## match versions like:
# sros-vm-22.10.R3.qcow2
# sros-vm-23.3.R1.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\+\.[0-9]\+\.[A-Z][0-9]\+\(-[0-9]\+\)\?\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
