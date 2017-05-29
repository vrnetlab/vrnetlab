# vqfx10k-re-15.1X53-D60.vmdk
VERSION=$(shell echo $(IMAGE) | sed -e 's/^vqfx10k-re-\([0-9][0-9]\.[0-9][A-Z][0-9]\+\(\.[0-9]\+\)\?\(-D[0-9]\+\)\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

usage:
	@echo "Usage: put the Juniper vQFX .vmdk files for the -re- and -pfe- in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .vmdk files"

# vqfx10k-pfe-20160609-2.vmdk
# TODO: we should make sure we only copy one PFE image (the latest?), in case there are many
docker-pre-build:
	cp vqfx10k-pfe*.vmdk docker/
