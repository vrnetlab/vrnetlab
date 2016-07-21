NUM_IMAGES=$(shell ls *.vmdk* 2>/dev/null| wc -l)
IMAGES=$(shell ls *.vmdk* 2>/dev/null)
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9]\(\.[0-9A-Z]\+\)\?\)\([^0-9]\+\|$$\)/\1/')
-include ../makefile.include

usage:
	@echo "Usage: put the Cisco IOS XRv vmdk image in this directory and run:"
	@echo "  make docker-image"

no-image:
	@echo "ERROR: you have no .vmdk image"

more-than-one-image:
	@echo "ERROR: you have more than one .vmdk image"
