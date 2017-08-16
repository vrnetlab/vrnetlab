vrnetlab / Juniper vQFX
=======================
This is the vrnetlab docker image for Juniper vQFX.

Building the docker image
-------------------------
Download vQFX from http://www.juniper.net/support/downloads/?p=vqfxeval#sw
Put the two .vmdk files in this directory and run `make` to produce a docker
image named `vr-vqfx`. The version tag of the image will be the same as the
JUNOS version, e.g. vqfx10k-re-15.1X53-D60.vmdk will produce an image called
vr-vqfx:15.1X53-D60.

Please note that you should always specify the version number of the docker
image when running your router. Docker defaults to using 'latest' 
Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

Tested with:
 * vqfx10k-re-15.1X53-D60.vmdk  MD5:758669e88213fbd7943f5da7f6d7bd59

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-vmx-router vr-vmx
```
It takes a couple of minutes for the virtual router to start and after this we
can login over SSH / NETCONF with the specified credentials (defaults to
vrnetlab / VR-netlab9).

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.

The vPFE has a serial port that is exposed on TCP port 5001. Normally you don't
need to interact with it but I imagine it could be useful for some debugging.
The vPFE of the vQFX doesn't send it's output to serial per default so you have
to catch it very early on in the boot so you can modify the GRUB parameters
(press 'e' to do that) and add console=ttyS0 to the "linux..." line.

System requirements
-------------------
CPU: 2 cores

RAM: 4096MB

Disk: 1.5GB

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Do you have a question?
A: Uhhhh
