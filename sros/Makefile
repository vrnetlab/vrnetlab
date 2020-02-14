VENDOR=Nokia
NAME=VSR
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# sros-vm-13.0.R7.qcow2
# sros-vm-14.0.R4.qcow2
# sros-vm-14.0.R7.qcow2
# sros-vm-15.0.R1.qcow2
# sros-vm-16.0.B0.qcow2 (pre-GA / beta image for 16, which is named completely differently when coming from Nokia)
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\+\.[0-9]\+\.[A-Z][0-9]\+\(-[0-9]\+\)\?\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
