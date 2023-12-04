VENDOR=Juniper
NAME=vJunosEvolved
IMAGE_FORMAT=qcow
IMAGE_GLOB=*.qcow2

# match versions like:
# vJunosEvolved-23.1R1.8.qcow2
# vJunosEvolved-22.1R2.2.qcow2
# vJunosEvolved-21.2R4.3.qcow2
# ...

VERSION=$(shell echo $(IMAGE) | sed -e 's/vjunosevolved-//i' | sed -e 's/.qcow2//i')

-include ../makefile-sanity.include
-include ../makefile.include
