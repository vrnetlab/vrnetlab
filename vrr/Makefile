VENDOR=Juniper
NAME=vRR
IMAGE_FORMAT=vmdk
IMAGE_GLOB=*.vmdk

# match versions like:
# junos-x86-64-19.3R3-S1.3.vmdk
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9][0-9]\.[0-9][A-Z][0-9]\+\(\.[0-9]\+\|-S[0-9]\+\(\.[0-9]\+\)\?\)\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
