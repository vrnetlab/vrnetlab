VENDOR=Juniper
NAME=vQFX
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# vqfx10k-re-15.1X53-D60.vmdk
# New vqfx are named: vqfx-19.4R1.10-re-qemu.qcow2
VERSION=$(shell echo $(IMAGE) |  sed -e 's/^vqfx-//'|sed -e 's/-re-qemu.qcow2//' )

PFE_BASE_VERSION=$(shell echo $VERSION | sed -e s'/.*//')
PFE_IMAGE=$(shell ls vqfx-$(PFE_BASE_VERSION)*-pfe-qemu.qcow*)

-include ../makefile-sanity.include
-include ../makefile.include

# TODO: we should make sure we only copy one PFE image (the latest?), in case there are many
docker-pre-build:
	echo "pfe     $(PFE_IMAGE)"
	cp vqfx*-pfe*.qcow* docker/
	echo "image   $(IMAGE)"
	echo "version $(VERSION)"

# mostly copied from makefile.include, i wish this was easier to change
docker-build-common: docker-clean-build docker-pre-build
	@if [ -z "$$IMAGE" ]; then echo "ERROR: No IMAGE specified"; exit 1; fi
	@if [ "$(IMAGE)" = "$(VERSION)" ]; then echo "ERROR: Incorrect version string ($(IMAGE)). The regexp for extracting version information is likely incorrect, check the regexp in the Makefile or open an issue at https://github.com/plajjan/vrnetlab/issues/new including the image file name you are using."; exit 1; fi
	@echo "Building docker image using $(IMAGE) as $(REGISTRY)vr-$(VR_NAME):$(VERSION)"
	cp ../common/* docker/
	$(MAKE) IMAGE=$$IMAGE docker-build-image-copy
	(cd docker; docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) --build-arg RE_IMAGE=$(IMAGE) --build-arg PFE_IMAGE=$(PFE_IMAGE) -t $(REGISTRY)vr-$(VR_NAME):$(VERSION) .)
