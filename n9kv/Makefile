VENDOR=Cisco
NAME=NXOS 9000v
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like: nxosv.9.2.4.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+\([0-9]\.[0-9]\.[0-9]\)\([^0-9].*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
