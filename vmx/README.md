# vrnetlab / Juniper vMX

This is the vrnetlab docker image for Juniper vMX.

> Originally developed by Kristian Larsson (@plajjan), adapted by @hellt to be integrated with [containerlab](https://containerlab.srlinux.dev) networking.  

## Added in this fork

* integration with containerlab as [vr-vmx](https://containerlab.srlinux.dev/manual/kinds/vr-vmx/) kind.
* docker networking using `--connection-mode` flag
* hostname, username and password configuration via flags
* added support for [boot delay](https://containerlab.srlinux.dev/manual/vrnetlab/#boot-delay) to allow for a smooth start of the big topologies
* enabled gNMI
* fixes for auto image upgrade disrupted node config
* base image updated to Ubuntu:20.04

## Building the docker image
Download vMX from http://www.juniper.net/support/downloads/?p=vmx#sw
Put the .tgz file in this directory and run `make` and you should be good to
go. The resulting image is called `vrnetlab/vr-vmx`. During the build it is normal to
receive some error messages about files that do not exist, like;

    mv: cannot stat '/tmp/vmx*/images/jinstall64-vmx*img': No such file or directory
    mv: cannot stat '/tmp/vmx*/images/vPFE-lite-*.img': No such file or directory

This is because different versions of JUNOS use different filenames.

The build of vMX is excruciatingly slow, often taking 10-20 minutes. This is
because the first time the VCP (control plane) starts up, it reads a config
file that controls whether it should run as a VRR of VCP in a vMX.

It's been tested to boot, respond to SSH and have correct interface mapping
with the following images:

* vmx-bundle-20.2R1.10.tgz


## System requirements

CPU: 4 cores - 3 for the vFPC (virtual FPC - the forwarding plane) and 1 for
VCP (the RE / control plane).

RAM: 6GB - 2 for VCP and 4 for vFPC

Disk: ~5GB for JUNOS 15.1, ~7GB for JUNOS 16 (I know, it's huge!!)
