VENDOR=Arista
NAME=vEOS
IMAGE_FORMAT=vmdk
IMAGE_GLOB=*.vmdk

# match versions like:
# vEOS-lab-4.16.6M.vmdk
# vEOS-lab-4.16.14M.vmdk
# vEOS-lab-4.17.1.1F.vmdk
# vEOS-lab-4.17.1F.vmdk
# vEOS-lab-4.20.0-EFT2.vmdk
VERSION=$(shell echo $(IMAGE) | sed -e 's/.*-\([0-9]\.\([0-9]\+\.\)\{1,2\}[0-9]\{1,2\}\([A-Z]\|\-EFT[0-9]\)\)\.vmdk$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

docker-pre-build:
	# checking if ZTP config contains a string (DISABLE=True) in the file /zerotouch-config
	# if it does, we don't need to write this file
	@echo Checking ZTP status
	ZTPOFF=$(shell docker run --rm -it -e LIBGUESTFS_DEBUG=0 -v $$(pwd):/work cmattoon/guestfish --ro -a $(IMAGE) -m /dev/sda2 cat /zerotouch-config 2> /dev/null || echo "false"); \
	echo "$@: ZTPOFF is $$ZTPOFF" && \
    if [ "$$ZTPOFF" != "DISABLE=True" ]; then \
      echo "Disabling ZTP" && docker run --rm -it -e LIBGUESTFS_DEBUG=0 -v $$(pwd):/work cmattoon/guestfish -a $(IMAGE) -m /dev/sda2 write /zerotouch-config "DISABLE=True"; \
    fi