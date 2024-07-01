VENDOR=Nokia
NAME=VSR
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2


## match versions like:
# sros-vm-22.10.R3.qcow2
# sros-vm-23.3.R1.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/\(magc-\)\?.\+[^0-9]\([0-9]\+\.[0-9]\+\.[A-Z][0-9]\+\(-[0-9]\+\)\?\)[^0-9].*$$/\1\2/')

-include ../makefile-sanity.include
-include ../makefile.include
