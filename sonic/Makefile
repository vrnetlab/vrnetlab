VENDOR=Sonic
NAME=sonic-vs
IMAGE_FORMAT=qcow
IMAGE_GLOB=*.qcow2
IMAGE=sonic-vs-202305.qcow2

# match versions like:
# 202305
VERSION=$(shell echo $(IMAGE) | sed -e 's/sonic-vs-//' | sed -e 's/.qcow2//')

-include ../makefile-sanity.include
-include ../makefile.include
