vrnetlab / Cisco IOS XRv9k
==========================
This is the vrnetlab docker image for Cisco IOS XRv9k.

There are two flavours of virtual XR routers, XRv and XRv9k where the latter
has a much more complete forwarding plane. This is for XRv9k if you have the
non-9k see the 'xrv' directory instead.

I've not tested XRv9k with less than 4 cores and 8G of RAM.

Building the docker image
-------------------------
Obtain the XRv9k release from Cisco. They generally ship an iso for a custom
install as well as a pre-built qcow2 image. Some releases the pre-built qcow2
is quite large, so making your own from the iso is recommended. At some point
we may support creating qcow2 from iso in vrnetlab, but that is currently not
supported.

Put the .qcow2 file in this directory and run `make docker-image` and you
should be good to go. The resulting image is called `vr-xrv9k`. You can tag it
with something else if you want, like `my-repo.example.com/vr-xrv` and then
push it to your repo. The tag is the same as the version of the XRv9k image,
so if you have xrv9k-fullk9-x.vrr-6.2.1.qcow2 your final docker image will be 
called vr-xrv9k:6.2.1

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to boot and respond to SSH with:

 * 6.1.3 (xrv9k-fullk9-x.vrr-6.1.3.qcow2)
 * 6.2.1 (xrv9k-fullk9-x.vrr-6.2.1.qcow2)
 * xrv9k-fullk9-x-6.4.2.qcow2	MD5:6958763192c7bb59a1b8049d377de1b4

Usage
-----
```
docker run -d --privileged --name my-xrv-router vr-xrv9k
```
You can run the image with `--privileged` to make use of KVM's hardware
assisted virtualisation, without which CPU emulation will be used instead.
Although I haven't measured, I imagine `--privileged` results in a considerable
performance boost over emulation. Further, emulation mode hasn't been as
thoroughly tested.

It takes about 150 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: What is the difference between XRv and XRv9k?
A: Cisco is probably better at giving a thorough answer to this question but
essentially XRv is meant for low-throughput labs while XRv9k has a much
higher performing forwarding plane that can be used for forwarding of
production traffic.

##### Q: How many NICs are supported?
A: Cisco specifies a maximum of 11 NICs but that seems to be balooney as it
successfully starts with 226 NICs. Be aware though that the startup time scales
linearly with the number of interfaces so unless you actually need a lot of
interfaces it is better to start it with fewer. The default is set to 24 which
felt like a good compromise and also means only a single PCI bus is needed,
which just felt like a good thing.

##### Q: Is a license required?
A: Yes and no. XRv9k can run in a demo mode or a production mode, where the
former is free and the latter cost money.

##### Q: How come CVAC is not used to feed the initial configuration?
A: CVAC uses a virtual CD-ROM drive to feed an initial configuration into XR.
Unfortuately it doesn't support generating crypto keys, which is required for
SSH, and so it cannot replace the serial approach to 100% and therefore I opted
to do everything over the serial interface.
