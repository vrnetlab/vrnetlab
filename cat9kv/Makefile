VENDOR=Cisco
NAME=cat9kv
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# csr1000v-universalk9.16.03.01a.qcow2
# csr1000v-universalk9.16.04.01.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\+\.[0-9]\+\.[0-9]\+[a-z]\?\)\([^0-9].*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include