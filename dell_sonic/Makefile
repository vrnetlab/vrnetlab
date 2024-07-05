VENDOR=Sonic
NAME=dell_sonic
IMAGE_FORMAT=qcow
IMAGE_GLOB=*.qcow2

# match versions like:
# 4.2.1
VERSION=$(shell echo $(IMAGE) | sed -e 's/dell-sonic-//' | sed -e 's/.qcow2//')

-include ../makefile-sanity.include
-include ../makefile.include
