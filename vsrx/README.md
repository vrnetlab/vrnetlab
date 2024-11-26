vrnetlab / Juniper vSRX
==================================
This is the vrnetlab docker image for Juniper vSRX.


Building the docker image
-------------------------
The image can be downloaded automatically using ```./get-vsrx.sh```. The script will download the official Juniper Vagrant box (216 MB), uncompress it and convert the vSRX image to a QCOW2 format.
Run ```make docker-image``` to build the docker image.

Tested booting and responding to SSH:
 * ffp-12.1X47-D15.4-packetmode.qcow2   MD5:692628eb87e067db33459a0030ec81b0

Usage
-----
```
docker run -d --privileged --name my-vsrx-box vr-vsrx:12.1X47-D15.4
```


System requirements
-------------------
CPU: 2 core

RAM: 2GB

Disk: <1GB

https://www.juniper.net/documentation/en_US/firefly12.1x46-d10/topics/reference/general/security-virtual-perimeter-system-requirement-with-kvm.html


FAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. It starts and you can connect to it. Take it for a spin and provide
some feedback :-)
