VENDOR=HP
NAME=VSR1000
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qco

# match versions like:
# VSR1000_HPE-CMW710-R0326-X64.qcow
# VSR1000_HPE-CMW710-E0321P01-X64.qco
VERSION=$(shell echo $(IMAGE) | sed -n 's/.*CMW\([0-9]\)\([0-9]\+\)-\([ER][0-9][0-9][0-9][0-9]\).*/\1.\2-\3/p')

-include ../makefile-sanity.include
-include ../makefile.include

