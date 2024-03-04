VENDOR=Ekinops
NAME=OneOS-OVP
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# OneOS-OVP-X86_pi2-6.10.2m5_3.7.5.qcow2 -> 3.7.5
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+_\([0-9.]\+\)\.$(IMAGE_FORMAT)$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
