VENDOR=Cisco
NAME=NXOS Titanium
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# TODO: add example file names here
# possible file names
# titanium-final.7.3.0.d1.1.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9]\.[A-Za-z][0-9]\.[0-9]\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
