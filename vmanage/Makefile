VENDOR=Cisco
NAME=vManage
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# viptela-vmanage-20.1.12-genericx86-64.qcow2
# viptela-vmanage-20.1.1-genericx86-64.qcow2
# viptela-vmanage-19.3.0-genericx86-64.qcow2
VERSION=$(shell echo $(IMAGE) | sed -n 's/.*\([0-9]\{2\}\.[0-9]\{1,2\}\.[0-9]\{1,2\}\).*/\1/p')

-include ../makefile-sanity.include
-include ../makefile.include
