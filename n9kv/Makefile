VENDOR=Cisco
NAME=NXOS 9000v
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2

# Match versions similar to the following:
# - nxosv-final.7.0.3.I7.5a.qcow2
# - nxosv-final.7.0.3.I7.9.qcow2
# - nxosv.9.2.1.qcow2
# - nxosv.9.2.4.qcow2
# - nexus9300v.9.3.9.qcow2
# - nexus9300v.9.3.10.qcow2
# - nexus9300v64.10.2.2.F.qcow
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+\?\.\(\(7\.0\.3\.I[0-9]\.[0-9a-z]\+\)\|\([0-9]\+\.[0-9]\+\.[0-9]\+\)\)\(\..*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
