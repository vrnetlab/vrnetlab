VENDOR=Juniper
NAME=vQFX
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# New vqfx are named: vqfx-19.4R1.10-re-qemu.qcow2
VERSION=$(shell echo $(IMAGE) |  sed -e 's/^vqfx-//'|sed -e 's/-re-qemu.qcow2//' )
# Old QFX are named: vqfx10k-re-15.1X53-D60.vmdk, and vqfx10k-re-18.4R1.8.vmdk and vqfx10k-pfe-18.4R1.8.vmdk so we need that version number extracted to convert them. 
VMDK_VERSION:=$(shell ls *-re-*.vmdk | sed -re 's/vqfx10k-re-([^;]*)\.vmdk.*$$/\1/')

PFE_BASE_VERSION=$(shell echo $VERSION | sed -e s'/.*//')
PFE_IMAGE=$(shell ls vqfx-$(PFE_BASE_VERSION)*-pfe-qemu.qcow*)

-include ../makefile-sanity.include
-include ../makefile.include

format-legacy-images:
	@if ls *.vmdk; then echo "VMDKs exist, converting them to qcow format"; qemu-img convert -f vmdk -O qcow2 *-re-*.vmdk vqfx-$(VMDK_VERSION)-re-qemu.qcow2 && qemu-img convert -f vmdk -O qcow *-pfe-*.vmdk vqfx-$(VMDK_VERSION)-pfe-qemu.qcow; echo "VMDKs have been converted"; fi

# TODO: we should make sure we only copy one PFE image (the latest?), in case there are many
docker-pre-build:

	echo "pfe     $(PFE_IMAGE)"
	cp vqfx*-pfe*.qcow* docker/
	echo "image   $(IMAGE)"
	echo "version $(VERSION)"

# mostly copied from makefile.include, i wish this was easier to change
docker-build-common: docker-clean-build docker-pre-build
	@if [ -z "$$IMAGE" ]; then echo "ERROR: No IMAGE specified"; exit 1; fi
	@if [ "$(IMAGE)" = "$(VERSION)" ]; then echo "ERROR: Incorrect version string ($(IMAGE)). The regexp for extracting version information is likely incorrect, check the regexp in the Makefile or open an issue at https://github.com/hellt/vrnetlab/issues/new including the image file name you are using."; exit 1; fi
	@echo "Building docker image using $(IMAGE) as $(REGISTRY)vr-$(VR_NAME):$(VERSION)"
	cp ../common/* docker/
	$(MAKE) IMAGE=$$IMAGE docker-build-image-copy
	(cd docker; docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) --build-arg RE_IMAGE=$(IMAGE) --build-arg PFE_IMAGE=$(PFE_IMAGE) -t $(REGISTRY)vr-$(VR_NAME):$(VERSION) .)
