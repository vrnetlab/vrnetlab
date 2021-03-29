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

Obtain the XRv9k release from Cisco. They generally ship an iso for a custom
install as well as a pre-built qcow2 image. Some releases the pre-built qcow2
is quite large, so making your own from the iso is recommended. At some point
we may support creating qcow2 from iso in vrnetlab, but that is currently not
supported.

Put the .qcow2 file in this directory and run `make docker-image` and you
should be good to go. The resulting image is called `vrnetlab/vr-xrv9k`. You can tag it
with something else if you want, like `my-repo.example.com/vr-xrv` and then
push it to your repo. The tag is the same as the version of the XRv9k image,
so if you have xrv9k-fullk9-x.vrr-6.2.1.qcow2 your final docker image will be 
called vr-xrv9k:6.2.1

It's been tested to boot and respond to SSH with:

 * xrv9k-fullk9-x-7.2.1.qcow2
