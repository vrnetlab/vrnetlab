# vrnetlab / Cisco IOS XRv9k
This is the vrnetlab docker image for Cisco IOS XRv9k.

> Originally developed by Kristian Larsson (@plajjan), adapted by @hellt to be integrated with [containerlab](https://containerlab.srlinux.dev) networking.  

There are two flavours of virtual XR routers, XRv and XRv9k where the latter
has a much more complete forwarding plane. This is for XRv9k if you have the
non-9k see the 'xrv' directory instead.

## Added in this fork

* integration with containerlab as [vr-xrv9k](https://containerlab.srlinux.dev/manual/kinds/vr-xrv9k/) kind.
* docker networking using `--connection-mode` flag
* Added `vcpu` and `ram` flags to tune the resources allocated to XRv VM
* hostname, username and password configuration via flags
* added support for [boot delay](https://containerlab.srlinux.dev/manual/vrnetlab/#boot-delay) to allow for a smooth start of the big topologies
* enabled gNMI
* qemu arguments were augmented with `-machine smm=off` and `-boot order=c` values to allow XRv 7 to boot.
* base image updated to Ubuntu:20.04

## Building the docker image

By default the XRv9k build time will take ~20 minutes as the image undergoes a first boot installation phase. This greatly decreases boot times for your labs.

The install procedure introduces some side effects as various values (such as macpool) are baked-in during this installation procedure.

This can cause issues, and for this reason you may want to disable the pre-install procedure. You can do this by issuing:

```
make docker-image INSTALL=false
```

> Please note that disabling the install feature will mean the boot time of XRv9k will increase to 20+ minutes.

### Installation steps

1. Obtain the XRv9k image (.qcow2) from Cisco (or CML). A .iso version is also shipped but this is currently unsupported and you must convert the .iso to .qcow2.

2. Place the .qcow2 file in this directory

3. Perform `make docker-image` (or `make docker-image INSTALL=false`)

4. Begin labbing. The image will be listed as `vrnetlab/vr-xrv9k` 

> The tag is the same as the version of the XRv9k image,
so if you have xrv9k-fullk9-x.vrr-6.2.1.qcow2 your final docker image will be called vr-xrv9k:6.2.1

## Known working versions

It's been tested to boot and respond to SSH with:

 * xrv9k-fullk9-x-7.2.1.qcow2
 * xrv9k-fullk9-x-7.7.1.qcow2
 * xrv9k-fullk9-x-7.11.1.qcow2

