VENDOR=Arista
NAME=vEOS
IMAGE_FORMAT=vmdk
IMAGE_GLOB=vEOS-lab*.vmdk

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
	cp *.iso docker/
