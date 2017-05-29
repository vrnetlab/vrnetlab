VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9]\(\.[0-9A-Z]\+\)\?\)\([^0-9].*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

usage:
	@echo "Usage: put the Cisco IOS XRv vmdk image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .vmdk image"
