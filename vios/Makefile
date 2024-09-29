VENDOR=Cisco
NAME=vIOS
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# Match images like:
# - cisco_vios-158-3.M2.qcow2
# Extract version cisco_vios and qcow2, for example: 158-3.M2
VERSION=$(shell echo $(IMAGE) | sed -e 's/cisco_vios-\(.*\)\.qcow2/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
