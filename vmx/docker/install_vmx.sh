#!/bin/sh

echo "Installing Juniper vMX"
tar -zxvf /vmx.tgz -C /tmp/ --wildcards vmx*/images/*img --wildcards vmx*/images/*qcow2
mkdir /vmx
mv -v /tmp/vmx*/images/vmxhdd.img /vmx/vmxhdd.img
mv -v /tmp/vmx*/images/junos-vmx*qcow2 /vmx/vmx.img	# 16.1 and newer
mv -v /tmp/vmx*/images/jinstall64-vmx*img /vmx/vmx.img
ls /tmp/vmx*/images
# vFPC / vPFE
mv -v /tmp/vmx*/images/vPFE-2*.img /vmx/vfpc.img	# 14.1
mv -v /tmp/vmx*/images/vFPC*.img /vmx/vfpc.img		# 15.1 and newer
mv -v /tmp/vmx*/images/metadata-usb-*.img /vmx/
mv -v /tmp/vmx*/images/metadata_usb.img /vmx/metadata-usb-re.img	# old style
# clean up
rm -rfv /vmx.tgz /tmp
