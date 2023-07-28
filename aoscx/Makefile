VENDOR=Aruba
NAME=ArubaOS-CX
IMAGE_FORMAT=vmdk
IMAGE_GLOB=*.vmdk

# match versions like:
# arubaoscx-disk-image-genericx86-p4-20230531220439.vmdk
VERSION=$(shell echo $(IMAGE) | sed -rn 's/.*arubaoscx-disk-image-genericx86-p4-(.+)\.vmdk/\1/p')

-include ../makefile-sanity.include
-include ../makefile.include
