VENDOR=Nokia
NAME=VSR
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

## The system environment variables will be used as http and https
## proxies.  They may be specifically overridden.  
## If the system environment variables are not set no proxy will
## be used.
##
## Example overrides
#http_proxy=http://192.168.1.1:3128
#https_proxy=http://192.168.1.1:3128
http_proxy=$(HTTP_PROXY)
https_proxy=$(HTTPS_PROXY)

## match versions like:
# sros-vm-22.10.R3.qcow2
# sros-vm-23.3.R1.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\+\.[0-9]\+\.[A-Z][0-9]\+\(-[0-9]\+\)\?\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
