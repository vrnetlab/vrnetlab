# match versions like:
# VSR1000_HPE-CMW710-R0326-X64.qcow
VERSION=$(shell echo $(IMAGE) | sed -n 's/.*\([R][0-9][0-9][0-9][0-9]\).*/\1/p')

#VERSION=R0326

-include ../makefile-sanity.include
-include ../makefile.include

usage:
	@echo "Usage: put the HP VSR1000 qcow2 image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .qcow2 image"
