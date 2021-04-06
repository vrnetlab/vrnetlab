# vrnetlab / Arista vEOS

This is the vrnetlab docker image for Arista vEOS.

> Originally developed by Kristian Larsson (@plajjan), adapted by @hellt to be integrated with [containerlab](https://containerlab.srlinux.dev) networking.  

## Added in this fork

* integration with containerlab as [vr-vmx](https://containerlab.srlinux.dev/manual/kinds/vr-vmx/) kind.
* docker networking using `--connection-mode` flag
* hostname, username and password configuration via flags
* added support for [boot delay](https://containerlab.srlinux.dev/manual/vrnetlab/#boot-delay) to allow for a smooth start of the big topologies
* enabled gNMI
* fixes for auto image upgrade disrupted node config
* fixes to boot vEOS64 image
* base image updated to Ubuntu:20.04

## Building the docker image
Download vEOS in vmdk format from https://www.arista.com/en/support/software-download
Place the .vmdk file in this directory and run make. The resulting images is called `vrnetlab/vr-veos`. You can
tag it with something else if you want, like `my-repo.example.com/vr-veos` and
then push it to your repo. 


It's been tested to boot, respond to SSH and have correct interface mapping
with the following images:

 * vEOS64-lab-4.25.2F


## System requirements

* CPU: 1 core
* RAM: 2GB
* Disk: <1GB

