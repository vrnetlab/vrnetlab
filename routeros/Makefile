VENDOR=Mikrotik
NAME=RouterOS
IMAGE_FORMAT=vmdk
IMAGE_GLOB=*.vmdk

# match versions like:
# chr-6.39.2.vmdk
VERSION=$(shell echo $(IMAGE) | sed -rn 's/.*chr-(.+)\.vmdk/\1/p')

-include ../makefile-sanity.include
-include ../makefile.include
