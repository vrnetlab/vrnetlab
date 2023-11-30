VENDOR=OpenBSD
NAME=OpenBSD
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# openbsd-7.2-2022-11-06.qcow2
# openbsd-7.3-2023-04-22.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/openbsd-\([0-9]\.[0-9]\)-.*/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

download:
	/bin/bash download.sh

build: download
	$(MAKE) docker-image