vrnetlab / Juniper vQFX
=======================
This is the vrnetlab docker image for Juniper vQFX.

Building the docker image
-------------------------
Bla

Tested with:
 * vqfx10k-re-15.1X53-D60.vmdk  MD5:758669e88213fbd7943f5da7f6d7bd59

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-vmx-router vr-vmx
```
It takes a couple of minutes for the virtual router to start and after this we
can login over SSH / NETCONF with the specified credentials.

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.

The vPFE has a serial port that is exposed on TCP port 5001. Normally you don't
need to interact with it but I imagine it could be useful for some debugging.

System requirements
-------------------
CPU: ?

RAM: ?

Disk: ?

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Does this work?
A: Nope.
