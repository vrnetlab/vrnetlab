vrnetlab / HP VSR1000
======================
This is the vrnetlab docker image for HP VSR1000.

Building the docker image
-------------------------
Download the HPE VSR1001 image here https://h10145.www1.hpe.com/downloads/SoftwareReleases.aspx?ProductNumber=JG811AAE&lang=&cc=&prodSeriesId= .
The current release is "VSR1000_7.10.R0326-X64".

Usage
-----
```
make docker-image
docker run -d --privileged --name my-vsr-router vr-vsr:R0326
```

System requirements
-------------------
CPU: 1 core

RAM: 2GB

Disk: <1GB

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. It starts and you can connect to it. Please do try it out and let me know if it works.
