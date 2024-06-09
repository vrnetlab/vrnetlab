VENDOR=Canonical
NAME=Ubuntu
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# jammy-ubuntu-cloud.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/\([a-z]\+\)-ubuntu-cloud.*/\1/')


-include ../makefile-sanity.include
-include ../makefile.include

download:
	/bin/bash download.sh

build: download
	$(MAKE) docker-image