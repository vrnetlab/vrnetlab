vrnetlab / Cisco Catalyst SD-WAN (Viptela) vEdge
==================================
This is the vrnetlab docker image for Cisco SD-WAN (Viptela) vEdge.

Building the docker image
-------------------------
* Download the Cisco SD-WAN vEdge image from https://software.cisco.com/download/
  * Select the "vEdge New Deployment KVM Image"
* Copy the qcow2 image into this folder, then run `make docker-image`.

Tested booting and responding to SSH :
* viptela-edge-20.11.1-genericx86-64.qcow2
* viptela-edge-20.12.2-genericx86-64.qcow2
* viptela-edge-20.12.4-genericx86-64.qcow2
* viptela-edge-20.3.1-genericx86-64.qcow2
* viptela-edge-20.6.1-genericx86-64.qcow2

Usage
-----
```
docker run -d --privileged --name my-vedge vrnetlab/vr-vedge:20.3.1
```

System requirements
-------------------
CPU: 2 cores

RAM: 2GB

Disk: 5GB

FAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
