VENDOR=Mikrotik
NAME=RouterOS
IMAGE_FORMAT=vmdk
IMAGE_GLOB=*.vmdk

# match versions like:
# chr-6.39.2.vmdk
VERSION=$(shell echo $(IMAGE) | sed -n 's/.*\([0-9]\.[0-9][0-99]\.[0-9]\).*/\1/p')

-include ../makefile-sanity.include
-include ../makefile.include
