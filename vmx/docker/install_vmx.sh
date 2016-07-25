#!/bin/sh

echo "Installing Juniper vMX"
tar -zxvf /vmx.tgz -C /tmp/ --wildcards vmx*/images/*img --wildcards vmx*/images/*qcow2
mkdir /vmx
mv -v /tmp/vmx*/images/vmxhdd.img /vmx/vmxhdd.img
mv -v /tmp/vmx*/images/junos-vmx*qcow2 /vmx/vmx.img
mv -v /tmp/vmx*/images/jinstall64-vmx*img /vmx/vmx.img
mv -v /tmp/vmx*/images/vFPC*img /vmx/vfpc.img
mv -v /tmp/vmx*/images/metadata-usb-*.img /vmx/ || mv -v /tmp/vmx*/images/metadata_usb.img /vmx/metadata-usb-re.img
rm -rfv /vmx.tgz /tmp
