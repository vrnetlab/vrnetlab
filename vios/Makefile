VENDOR=Cisco
NAME=vIOS
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# Match images like:
# - vios-adventerprisek9-m.SPA.158-3.M2.qcow2
# - vios-adventerprisek9-m.SPA.159-3.M6.qcow2
# Extract version between SPA and qcow2, for example: 158-3.159-3.M6
VERSION=$(shell echo $(IMAGE) | sed 's/.*SPA\.\(.*\)\.qcow2/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
