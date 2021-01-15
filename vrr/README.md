vrnetlab / Juniper vRR
=======================
This is the vrnetlab docker image for Juniper vRR.

Building the docker image
-------------------------
Download vRR from https://support.juniper.net/support/downloads/?p=virtual-route-reflector
Put the .vmdk file in this directory and run `make` to produce a docker
image named `vr-vrr`. The version tag of the image will be the same as the
JUNOS version, e.g. junos-x86-64-19.3R3-S1.3.vmdk will produce an image called
vr-vrr:19.3R3-S1.3.

Please note that you should always specify the version number of the docker
image when running your router. Docker defaults to using 'latest' 
Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

Tested with:
 * junos-x86-64-19.3R3-S1.3.vmdk SHA:c5dd964149b81fad722e03283d4c88d09b9652bb

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-vmx-router vr-vrr
```
It takes a couple of minutes for the virtual router to start and after this we
can login over SSH / NETCONF with the specified credentials (defaults to
vrnetlab / VR-netlab9).

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.

System requirements
-------------------
CPU: 1 cores

RAM: 2048MB

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Do you have a question?
A: Uhhhh
