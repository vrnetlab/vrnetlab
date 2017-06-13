vrnetlab / Mikrotik RouterOS (ROS)
==================================
This is the vrnetlab docker image for Mikrotik RouterOS (ROS).

Building the docker image
-------------------------
Download the Cloud Hosted Router VMDK image from https://www.mikrotik.com/download
Copy the vmdk image into this folder, then run `make docker-image`.

Tested booting and responding to SSH:
 * chr-6.39.2.vmdk   MD5:eb99636e3cdbd1ea79551170c68a9a27

Usage
-----
```
docker run -d --privileged --name my-ros-router vr-ros:6.39.2
```

System requirements
-------------------
CPU: 1 core

RAM: <1GB

Disk: <1GB

FAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. It starts and you can connect to it. Take it for a spin and provide
some feedback :-)
