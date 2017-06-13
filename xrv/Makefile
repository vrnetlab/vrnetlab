VENDOR=Cisco
NAME=XRv
IMAGE_FORMAT=vmdk
IMAGE_GLOB=*vmdk*

# match versions like:
# TODO: add example file names here
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9]\(\.[0-9A-Z]\+\)\?\)\([^0-9].*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
