# vrnetlab / ArubaOS-CX (aoscx)

This is the vrnetlab docker image for ArubaOS-CX.

## Building the docker image
Download the OVA image from [Aruba Support Portal](https://asp.arubanetworks.com/downloads/software/RmlsZTpkOGRiYjc2Ni0wMTdkLTExZWUtYTY3Yi00Zjg4YjUyOWExMzQ%3D), and extract the vmdk file from it.
Copy the vmdk image into this folder, then run `make docker-image`.

Tested booting and responding to SSH:
 * `ArubaOS-CX_10_12_0006.ova` (`arubaoscx-disk-image-genericx86-p4-20230531220439.vmdk`)


## System requirements
CPU: 2 core

RAM: 4GB

Disk: <1GB

