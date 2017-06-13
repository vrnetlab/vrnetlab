VENDOR=HP
NAME=VSR1000
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qco

# match versions like:
# VSR1000_HPE-CMW710-R0326-X64.qcow
VERSION=$(shell echo $(IMAGE) | sed -n 's/.*\([R][0-9][0-9][0-9][0-9]\).*/\1/p')

#VERSION=R0326

-include ../makefile-sanity.include
-include ../makefile.include

