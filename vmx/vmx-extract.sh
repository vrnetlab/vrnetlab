#!/bin/sh

IMAGE=$1

echo "Extracting Juniper vMX tgz"
rm -rf tmp docker/vmx
mkdir -p tmp docker/vmx
tar -zxvf ${IMAGE} -C tmp/ --wildcards vmx*/images/*img --wildcards vmx*/images/*qcow2
# VCP
# The 're' directory contains files for a standalone RE
mkdir -p docker/vmx/re
mv -v tmp/vmx*/images/vmxhdd.img docker/vmx/re
mv -v tmp/vmx*/images/junos-vmx*qcow2 docker/vmx/re		# 16.1 and newer
mv -v tmp/vmx*/images/jinstall64-vmx*img docker/vmx/re
mv -v tmp/vmx*/images/metadata-usb-re*.img docker/vmx/re
mv -v tmp/vmx*/images/metadata_usb.img docker/vmx/re/metadata-usb-re.img	# old style

# vFPC / vPFE
mv -v tmp/vmx*/images/vPFE-lite-*.img docker/vmx/vfpc.img	# 14.1
mv -v tmp/vmx*/images/vFPC*.img docker/vmx/vfpc.img		# 15.1 and newer
mv -v tmp/vmx*/images/metadata-usb-*.img docker/vmx/
mv -v tmp/vmx*/images/metadata_usb.img docker/vmx/metadata-usb-re.img	# old style
# clean up
rm -rfv tmp