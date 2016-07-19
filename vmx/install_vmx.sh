#!/bin/sh

echo "Installing Juniper vMX"
tar -zxvf /vmx.tgz -C /tmp/ --wildcards vmx*/images/*img
mkdir /vmx
mv -v /tmp/vmx*/images/vmxhdd.img /vmx/vmxhdd.img
mv -v /tmp/vmx*/images/jinstall64-vmx*img /vmx/jinstall64-vmx.img
mv -v /tmp/vmx*/images/vFPC*img /vmx/vfpc.img
mv -v /tmp/vmx*/images/metadata_usb.img /vmx/metadata_usb.img
rm -rfv /vmx.tgz /tmp
