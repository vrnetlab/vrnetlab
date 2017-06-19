VENDOR=OpenWRT
NAME=OpenWRT
IMAGE_FORMAT=img
IMAGE_GLOB=*.img

# match versions like:
# openwrt-15.05-x86-kvm_guest-combined-ext4.img
VERSION=$(shell echo $(IMAGE) | cut -d - -f 2)

-include ../makefile-sanity.include
-include ../makefile.include
