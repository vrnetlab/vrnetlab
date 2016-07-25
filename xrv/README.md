vrnetlab / Cisco IOS XRv
========================
This is the vrnetlab docker image for Cisco IOS XRv.

There are two flavours of virtual XR routers, XRv and XRv9000 where the latter
has a much more complete forwarding plane. This image is not tested with
XRv9000, which has a different dataplane and potentially different setup/boot
mechanics.

A maximum of 16 NICs is supported. While it is possible to have a higher number
of NICs on certain machines and with certain versions of XR, 16 is the number
that I've found that works consistently although I have not done extensive
testing.

It's not recommended to run XRv with less than 4GB of RAM. I have experienced
weird issues when trying to use less RAM.

Building the docker image
-------------------------
Download IOS XRv from
https://upload.cisco.com/cgi-bin/swc/fileexg/main.cgi?CONTYPES=Cisco-IOS-XRv
Put the .vmdk file in this directory and run `make docker-image` and you
should be good to go. The resulting image is called `vr-xrv`. You can tag it
with something else if you want, like `my-repo.example.com/vr-xrv` and then
push it to your repo. The tag is the same as the version of the XRv image,
so if you have iosxrv-k9-demo.vmdk-5.3.3 your final docker image will be called
vr-xrv:5.3.3

It's been tested to boot and respond to SSH with:

 * 5.1.3 (iosxrv-k9-demo-5.1.3.vmdk)
 * 5.2.2 (iosxrv-k9-demo-5.2.2.vmdk)
 * 5.3.0 (iosxrv-k9-demo-5.3.0.vmdk)
 * 5.3.2 (iosxrv-k9-demo-5.3.2.vmdk)
 * 5.3.3 (iosxrv-k9-demo.vmdk-5.3.3)
 * 5.3.3.51U (TeraStream build)
 * 6.0.0 (iosxrv-k9-demo-6.0.0.vmdk)
 * 6.0.1 (iosxrv-k9-demo.vmdk-6.0.1)

Usage
-----
```
docker run -d --privileged --name my-xrv-router vr-xrv
```
You can run the image with `--privileged` to make use of KVM's hardware
assisted virtualisation. Without which CPU emulation will be used instead.
Although I haven't measured I imagine `--privileged` results in a considerable
performance boost over emulation. Further, emulation mode hasn't been as
thoroughly tested.

It takes about 150 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.
