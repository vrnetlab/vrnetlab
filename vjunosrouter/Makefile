VENDOR=Juniper
NAME=vJunos-router
IMAGE_FORMAT=qcow
IMAGE_GLOB=*.qcow2

# match versions like:
# vJunos-router-23.2R1.15.qcow2
# ...
VERSION=$(shell echo $(IMAGE) | sed -e 's/vJunos-router-//i' | sed -e 's/.qcow2//i')

-include ../makefile-sanity.include
-include ../makefile.include