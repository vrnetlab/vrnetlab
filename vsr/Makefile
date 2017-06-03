# match versions like:
# VSR1000_HPE-CMW710-R0326-X64.qcow
#VERSION=$(shell echo $(IMAGE) | sed -e 's/.*-\([0-9]\.\([0-9]\+\.\)\{1,2\}[0-9][A-Z]\)\.vmdk$$/\1/')
VERSION=latest

-include ../makefile-sanity.include
-include ../makefile.include

docker-pre-build:
	cp *.qcow2 docker/

usage:
	@echo "Usage: put the HP VSR1000 qcow2 image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .qcow2 image"
