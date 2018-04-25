VENDOR=Cisco
NAME=XRv
IMAGE_FORMAT=vmdk
IMAGE_GLOB=*vmdk*

# match versions like:
# iosxrv-k9-demo-5.3.3.51U.vmdk
# iosxrv-k9-demo-6.1.2.vmdk
# iosxrv-k9-demo-6.2.2.15I.DT_IMAGE.vmdk
# iosxrv-k9-demo-6.2.2.1T-dhcpfix.vmdk
# iosxrv-k9-demo-6.2.2.22I.vmdk
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9][^0-9]\([0-9]\.[0-9]\.[0-9]\(\.[0-9A-Z]\+\)\?\)\([^0-9].*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include
