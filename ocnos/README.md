# vrnetlab / IPInfusion OcNOS

This is the vrnetlab docker image for IPInfusion OcNOS.

## Building the docker image

Download the OcNOS-VM image from https://www.ipinfusion.com/products/ocnos-vm/
Copy the qcow2 image into this folder, then run `make docker-image`.

Tested booting and responding to SSH:

- DEMO_VM-OcNOS-6.0.2.11-MPLS-x86-MR.qcow2 MD5:08bbaf99347c33f75d15f552bda762e1

## Serial console issues

The image of OcNOS version 6.0.2.11 distributed from the official website has a bug that prevents connection via serial console.
This problem can be corrected by modifying /boot/grub/grub.cfg in the image.

For example, it can be modified as follows

```
OCNOS_IMAGE="DEMO_VM-OcNOS-6.0.2.11-MPLS-x86-MR.qcow2"

modprobe nbd
qemu-nbd --connect=/dev/nbd0 $OCNOS_IMAGE
mkdir -p /tmp/OCNOS_ROOT
mount /dev/nbd0p1 /tmp/OCNOS_ROOT
sed -ie 's/\( *linux.*\)$/\1 console=ttyS0,115200n8/' /tmp/OCNOS_ROOT/boot/grub/grub.cfg
umount /tmp/OCNOS_ROOT
qemu-nbd --disconnect /dev/nbd0
```

## System requirements

CPU: 2 core

RAM: <4GB

Disk: <4GB

## Containerlab

Containerlab kind for OcNOS is [ipinfusion_ocnos](https://containerlab.dev/manual/kinds/ipinfusion-ocnos/).
