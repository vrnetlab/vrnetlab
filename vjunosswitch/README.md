# vrnetlab / Juniper vJunos-switch

This is the vrnetlab docker image for Juniper's vJunos-switch.

> Available with [containerlab](https://containerlab.dev) as vr-vjunosswitch.

## Building the docker image

Download the vJunos-switch .qcow2 image from  <https://www.juniper.net/us/en/dm/vjunos-labs.html>
and place it in this directory. After typing `make`, a new image will appear called `vrnetlab/vjunosswitch`.
Run `docker images` to confirm this.

## System requirements

CPU: 4 cores
RAM: 5GB
DISK: ~4.5GB
