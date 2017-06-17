vrnetlab / OpenWRT
==================================
This is the vrnetlab docker image for OpenWRT.

Building the docker image
-------------------------
Download an image from openwrt.org https://downloads.openwrt.org/chaos_calmer/15.05.1/x86/kvm_guest/ . Gunzip the file and run `make docker-image`.

As per OpenWRT defaults, `br-lan`(`eth0`) is the LAN interface and `eth1` the WAN interface.

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
