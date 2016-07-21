VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9][0-9]\.[0-9][A-Z][0-9]\+\.[0-9]\+\)[^0-9].*$$/\1/')
-include ../makefile.include

usage:
	@echo "Usage: put the Juniper vMX .tgz file in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .tgz file"

more-than-one-image:
	@echo "ERROR: you have more than one .tgz file"
