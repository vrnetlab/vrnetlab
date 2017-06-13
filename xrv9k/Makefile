VENDOR=Cisco
NAME=XRv9k
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*qcow2*

# match versions like:
# TODO: add example file names here
# xrv9k-fullk9-x.vrr-6.1.3.qcow2
# xrv9k-fullk9-x.vrr-6.2.1.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9]\(\.[0-9A-Z]\+\)\?\)\([^0-9].*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
