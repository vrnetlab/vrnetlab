VENDOR=Cisco
NAME=FTDv
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# match versions like:
# Cisco_Secure_Firewall_Threat_Defense_Virtual-7.2.5-208.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+-\([0-9]\+\.[0-9]\+\.[0-9]\+\)-[0-9]\+.*/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
-include ../makefile-install.include
