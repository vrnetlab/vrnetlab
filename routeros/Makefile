# match versions like:
# chr-6.39.2.vmdk
VERSION=$(shell echo $(IMAGE) | sed -n 's/.*\([0-9]\.[0-9][0-99]\.[0-9]\).*/\1/p')

-include ../makefile-sanity.include
-include ../makefile.include

usage:
	@echo "Usage: put the Mikrotik ROS vmdk image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .vmdk image"
