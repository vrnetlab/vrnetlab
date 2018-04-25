vrnetlab / OpenWRT
==================================
This is the vrnetlab docker image for OpenWRT.

Building the docker image
-------------------------
Run `make build` to automatically download images from the public OpenWRT image
repository and build them into vrnetlab docker images. `build` consists of the
`download` step and `docker-image` step, which can be run separately.

Use `make download` to automatically download images from the public OpenWRT
image repository at https://downloads.openwrt.org. The download script will get
everything that has a two-digit major version, e.g. 12.09, 14.07, 15.05 etc.

You can also download images manually by navigating to
https://downloads.openwrt.org/ and grabbing the file. You have to gunzip it.

Whichever way you get the images, once you have them, run `make docker-image`
to build the docker images. The resulting image is called `vr-openwrt`. You can
tag it with something else if you want, like `my-repo.example.com/vr-openwrt`
and then push it to your repo. The tag is the same as the version of the
OpenWRT image, so if you have openwrt-15.05-x86-kvm_guest-combined-ext4.img
your final docker image will be called vr-openwrt:15.05.

As per OpenWRT defaults, `br-lan`(`eth0`) is the LAN interface and `eth1` the
WAN interface.

Tested booting and responding to SSH:
* openwrt-15.05-x86-kvm_guest-combined-ext4.img   MD5:3d9b51a7e0cd728137318989a9fd35fb

Usage
-----
```
docker run -d --privileged --name openwrt1 vr-openwrt:15.05
```

System requirements
-------------------
CPU: 1 core

RAM: 128 MB

Disk: 256 MB

FAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. It starts and you can connect to it. Take it for a spin and provide
some feedback :-)
