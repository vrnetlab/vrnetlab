# vrnetlab / Juniper vJunos-router

This is the vrnetlab docker image for Juniper's vJunos-router. This is built from the vJunos-switch template.

## Building the docker image

Download the vJunos-router .qcow2 image from  <https://support.juniper.net/support/downloads/?p=vjunos-router>
and place it in this directory. After typing `make`, a new image will appear called `vrnetlab/vjunosrouter`.
Run `docker images` to confirm this.

## System requirements

CPU: 4 cores
RAM: 5GB
DISK: ~4.5GB
