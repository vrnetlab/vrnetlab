VENDOR=FreeBSD
NAME=FreeBSD
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# freebsd-13.2-zfs-2023-04-21.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/freebsd-\([0-9]\+\.[0-9]\)-.*/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

download:
	/bin/bash download.sh

build: download
	$(MAKE) docker-image