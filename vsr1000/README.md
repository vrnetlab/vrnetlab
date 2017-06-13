vrnetlab / HP VSR1000
=====================
This is the vrnetlab docker image for HP VSR1000.

Building the docker image
-------------------------
Download the HPE VSR1001 image from 
https://h10145.www1.hpe.com/downloads/SoftwareReleases.aspx?ProductNumber=JG811AAE
Unzip the downloaded zip file, place the .qco image in this directory and run
`make docker-image`. The tag is the same as the version of the VSR1000 image,
so if you have VSR1000_HPE-CMW710-R0326-X64.qco your docker image will be
called vr-vsr1000:7.10-R0326

Tested booting and responding to SSH:
 * VSR1000_HPE-CMW710-R0326-X64.qco   MD5:4153d638bfa72ca72a957ea8682ad0e2

Usage
-----
```
docker run -d --privileged --name my-vsr1000-router vr-vsr1000:7.10-R0326
```

System requirements
-------------------
CPU: 1 core

RAM: 1GB

Disk: <1GB

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. It starts and you can connect to it. Take it for a spin and provide some feedback :-)
