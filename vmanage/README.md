vrnetlab / Cisco Catalyst SD-WAN (Viptela) vManage
==================================
This is the vrnetlab docker image for Cisco Catalyst SD-WAN (Viptela) vManage.

Building the docker image
-------------------------
* Download the Cisco SD-WAN vManage image from https://software.cisco.com/download/
  * Select the "vManage New Deployment KVM Image"
* Copy the qcow2 image into this folder, then run `make docker-image`.

Tested booting and responding to SSH and HTTPS:
* viptela-vmanage-20.1.1-genericx86-64.qcow2
* viptela-vmanage-20.11.1-genericx86-64.qcow2
* viptela-vmanage-20.12.2-genericx86-64.qcow2
* viptela-vmanage-20.12.4-genericx86-64.qcow2
* viptela-vmanage-20.3.1-genericx86-64.qcow2
* viptela-vmanage-20.6.1-genericx86-64.qcow2

Usage
-----
```
docker run -d --privileged --name my-vmanage vrnetlab/vr-vmanage:20.1.1
```

System requirements
-------------------
CPU: 16 cores

RAM: 32GB

Disk: 5GB

FAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been tested?
A: Yes, I've used the vManage image in combination with vEdge and vSmart images
in a lab environment to test end-to-end connectivity over a VPN.

##### Q: Is there support for a vEdge and vSmart as well?
A: Yes, there is a vr-vedge and vr-vsmart image available as well.
