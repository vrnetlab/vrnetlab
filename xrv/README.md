vrnetlab / Cisco IOS XRv
========================
This is the vrnetlab docker image for Cisco IOS XRv.

There are two flavours of virtual XR routers, XRv and XRv9000 where the latter
has a much more complete forwarding plane. This is for XRv, if you have the
XRv9k see the 'xrv9k' directory instead.

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

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to boot and respond to SSH with:

 * 5.1.1.54U (TeraStream build)
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
##### Q: What is the difference between XRv and XRv9000?
A: Cisco is probably better at giving a thorough answer to this question but
essentially XRv is meant for low-throughput labs while XRv9000 has a much
higher performing forwarding plane that can be used for forwarding of
production traffic.

##### Q: Why not use XRv9000?
A: It seems that all the forwarding plane features that I am looking for are
available in XRv and so there is very little benefit to XRv9000. On the
contrary, XRv supports up to 128 interfaces
(http://www.cisco.com/c/en/us/td/docs/ios_xr_sw/ios_xrv/install_config/b-xrv/b-xrv_chapter_01.html)
with a single VM whereas XRv9000 seems to support up to 11 NICs (see
http://www.cisco.com/c/en/us/td/docs/routers/virtual-routers/configuration/guide/b-xrv9k-cg/b-xrv9k-cg_chapter_0111.html).

##### Q: How many NICs are supported?
A: 128, which is the maximum as specified by Cisco. I use multiple PCI buses to
reach this number and while the current setting is for 128 I have successfully
started XRv with more although I have not done any thorough testing.

##### Q: Is a license required?
A: Yes and no. XRv can run in a demo mode or a production mode, where the
former is free and the latter cost money. The download URL provided earlier is
to the free demo version. In the demo mode there are hard-coded users (i.e. not
very secure for production) and it is rate-limited to a total throughput of
2Mbps.

##### Q: How come CVAC is not used to feed the initial configuration?
A: CVAC uses a virtual CD-ROM drive to feed an initial configuration into XR.
Unfortuately it doesn't support generating crypto keys, which is required for
SSH, and so it cannot replace the serial approach to 100% and therefore I opted
to do everything over the serial interface.
