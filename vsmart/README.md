vrnetlab / Cisco Catalyst SD-WAN (Viptela) vSmart
==================================
This is the vrnetlab docker image for Cisco SD-WAN (Viptela) vSmart.

Building the docker image
-------------------------
* Download the Cisco SD-WAN vSmart image from https://software.cisco.com/download/
  * Select the "vSmart New Deployment KVM Image"
* Copy the qcow2 image into this folder, then run `make docker-image`.

Tested booting and responding to SSH :
* viptela-smart-20.11.1-genericx86-64.qcow2
* viptela-smart-20.12.2-genericx86-64.qcow2
* viptela-smart-20.12.4-genericx86-64.qcow2
* viptela-smart-20.3.1-genericx86-64.qcow2
* viptela-smart-20.6.1-genericx86-64.qcow2

Usage
-----
```
docker run -d --privileged --name my-vsmart vrnetlab/vr-vsmart:20.3.1
```

System requirements
-------------------
CPU: 1 cores

RAM: 1GB

FAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
