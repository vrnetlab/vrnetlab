VENDOR=Cisco
NAME=NXOS Titanium
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# TODO: add example file names here
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9]\.[A-Z][0-9]\.[0-9]\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
