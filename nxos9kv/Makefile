VENDOR=Cisco
NAME=NX-OS 9000v
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# nexus9300v.9.3.7.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9].*\)\.qcow2$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

docker-pre-build:
	cp OVMF-pure-efi.fd nxos_config.txt docker
