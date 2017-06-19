VENDOR=OpenWRT
NAME=OpenWRT
IMAGE_FORMAT=img
IMAGE_GLOB=*.img

# match versions like:
# openwrt-12.09-x86-kvm_guest-combined-ext4.img
# openwrt-14.07-x86-kvm_guest-combined-ext4.img
# openwrt-15.05.1-x86-kvm_guest-combined-ext4.img
# openwrt-15.05-x86-kvm_guest-combined-ext4.img
VERSION=$(shell echo $(IMAGE) | sed -e 's/openwrt-\([0-9][0-9]\.[0-9][0-9]\(\.[0-9]\+\)\?\)-.*/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

download:
	python3 download.py
	for F in `ls *.img.gz`; do gunzip -f $$F; done

build: download
	$(MAKE) docker-image
