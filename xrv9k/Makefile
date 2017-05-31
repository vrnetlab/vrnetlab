VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\.[0-9]\.[0-9]\(\.[0-9A-Z]\+\)\?\)\([^0-9].*\|$$\)/\1/')
-include ../makefile.include

usage:
	@echo "Usage: put the Cisco IOS xrv9k qcow2 image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .qcow2 image"
