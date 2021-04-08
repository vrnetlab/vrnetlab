# vrnetlab / Mikrotik RouterOS (ROS)

This is the vrnetlab docker image for Mikrotik RouterOS (ROS).

## Building the docker image
Download the Cloud Hosted Router VMDK image from https://www.mikrotik.com/download
Copy the vmdk image into this folder, then run `make docker-image`.

Tested booting and responding to SSH:
 * chr-6.39.2.vmdk   MD5:eb99636e3cdbd1ea79551170c68a9a27
 * chr-6.47.9.vmdk
 * chr-7.1beta5.vmdk


## System requirements
CPU: 1 core

RAM: <1GB

Disk: <1GB

## Containerlab
Containerlab kind for routeros is [vr-ros](https://containerlab.srlinux.dev/manual/kinds/vr-ros/).
