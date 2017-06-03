# match versions like:
# vEOS-lab-4.16.6M.vmdk
# vEOS-lab-4.17.1.1F.vmdk
# vEOS-lab-4.17.1F.vmdk
VERSION=$(shell echo $(IMAGE) | sed -e 's/.*-\([0-9]\.\([0-9]\+\.\)\{1,2\}[0-9][A-Z]\)\.vmdk$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

usage:
	@echo "Usage: put the Cisco NXOS Titanium qcow2 image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .qcow2 image"
