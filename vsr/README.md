vrnetlab / HP VSR1000
======================
This is the vrnetlab docker image for HP VSR1000.

Building the docker image
-------------------------
Download the HPE VSR1001 image here https://h10145.www1.hpe.com/downloads/SoftwareReleases.aspx?ProductNumber=JG811AAE&lang=&cc=&prodSeriesId= .
The current release is "VSR1000_7.10.R0326-X64". Copy the QCO (qcow2) image into this folder, then run ``` make docker-image ```.

Tested booting and respond to SSH:
 * VSR1000_HPE-CMW710-R0326-X64.qco   MD5:4153d638bfa72ca72a957ea8682ad0e2

Usage
-----
```
docker run -d --privileged --name my-vsr-router vr-vsr:R0326
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
