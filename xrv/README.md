# vrnetlab / Cisco IOS XRv

This is the vrnetlab docker image for Cisco IOS XRv.

> Originally developed by Kristian Larsson (@plajjan), adapted by @hellt to be integrated with [containerlab](https://containerlab.srlinux.dev) networking.  

There are two flavours of virtual XR routers, XRv and XRv9000 where the latter
has a much more complete forwarding plane. This is for XRv, if you have the
XRv9k see the 'xrv9k' directory instead.

It's not recommended to run XRv with less than 4GB of RAM. I have experienced
weird issues when trying to use less RAM.

## Added in this fork

* integration with containerlab as [vr-vmx](https://containerlab.srlinux.dev/manual/kinds/vr-vmx/) kind.
* docker networking using `--connection-mode` flag
* hostname, username and password configuration via flags
* added support for [boot delay](https://containerlab.srlinux.dev/manual/vrnetlab/#boot-delay) to allow for a smooth start of the big topologies
* enabled gNMI
* fixes for auto image upgrade disrupted node config
* base image updated to Ubuntu:20.04

## Building the docker image

Obtain XRv vmkd image and put the .vmdk file in this directory and run `make docker-image`. The resulting image is called `vrnetlab/vr-xrv`. You can tag it with something else if you want, like `my-repo.example.com/vr-xrv` and then
push it to your repo. The tag is the same as the version of the XRv image, so if you have iosxrv-k9-demo.vmdk-5.3.3 your final docker image will be called `vrnetlab/vr-xrv:5.3.3`

 * 6.1.2
