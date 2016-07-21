VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9][0-9]\.[0-9]\.[A-Z][0-9]\+\(-[0-9]\+\)\?\)[^0-9].*$$/\1/')
-include ../makefile.include

usage:
	@echo "Usage: put the Nokia VSR qcow2 image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .qcow2 image"

more-than-one-image:
	@echo "ERROR: you have more than one .qcow2 image"
