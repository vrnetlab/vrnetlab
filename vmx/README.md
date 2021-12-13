vrnetlab / Juniper vMX
========================
This is the vrnetlab docker image for Juniper vMX.

Building the docker image
-------------------------
Download vMX from http://www.juniper.net/support/downloads/?p=vmx#sw
Put the .tgz file in this directory and run `make` and you should be good to
go. The resulting image is called `vr-vmx`. During the build it is normal to
receive some error messages about files that do not exist, like;

    mv: cannot stat '/tmp/vmx*/images/jinstall64-vmx*img': No such file or directory
    mv: cannot stat '/tmp/vmx*/images/vPFE-lite-*.img': No such file or directory

This is because different versions of JUNOS use different filenames.

The build of vMX is excruciatingly slow, often taking 10-20 minutes. This is
because the first time the VCP (control plane) starts up, it reads a config
file that controls whether it should run as a VRR of VCP in a vMX.  Previously
this start was performed during docker run but it meant that the VCP would
always restart once before the virtual router became available, thus leading to
long bootup times (like 5 minutes). This first start of the VCP is now done
during the build of the docker image and as docker build can't be run with
--privileged it means that qemu is running without hardware KVM acceleration
and thus taking a very long time. You will get a lot of trace output during
this process so at least you can see what's going on. I think it's worth the
longer build time since we build images few times but run them many.

The router can run in standalone mode (single routing engine) or redundant mode
(dual routing engines). This is controller with a runtime configuration options
`--dual-re`. At build time, we build the VCP machines for both modes of
operation: a standalone RE (files in `/vmx/re`) and dual RE (files in
`/vmx/re{0,1}`). At runtime the VCP(s) are started from the correct
directories.

The bootstrap configuration is provided to the device via a "config-drive".
During the install phase, the file `juniper.conf` is used to populate the
metadata-usb image that is attached to the device.

If you want, you can tag the resulting docker image with something else, like
`my-repo.example.com/vr-vmx` and then push it to your repo.  The tag is the
same as the version of the JUNOS image, so if you have vmx-15.1F4.15.tgz your
final docker image will be called vr-vmx:15.1F4.15.

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to boot, respond to SSH and have correct interface mapping
with the following images:

 * vmx-14.1R6.4.tgz  MD5:49d37693fc4c5971fe99703149b39776
 * vmx-15.1F4.15.tgz  MD5:86c28d89d6db5497521ebbb2c7de4472
 * vmx-bundle-15.1F6.9.tgz  MD5:eb128cffde6ab29fdb27b2f52301c5f9
 * vmx-bundle-16.1R1.7.tgz  MD5:d96766848731c12c0492e3ae2349b426
 * vmx-bundle-16.1R2.11.tgz  MD5:24bc389420bf02fb6ede36afa79a0a19
 * vmx-bundle-17.2R1.13.tgz  MD5:64569e60a2fd671aad565c7bd3745e88

It is NOT working with the following images:

 * vmx-15.1F3.11.tgz  MD5:978fc8c0db05179564d0680040db8196

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

The vFPC has a serial port that is exposed on TCP port 5002. Normally you don't
need to interact with it but I imagine it could be useful for some debugging.

You can provide additional configuration, to be merged with running
configuration on startup. Pass the complete configuration file in the correct
format in the `EXTRA_CONFIG` environment variable to the container.
Assuming you have the configuration stored in a file `extra-config.conf`, to
read it into an environment variable use this:

```
docker run --privileged -it --name vmx15 --env EXTRA_CONFIG="`cat extra-config.conf`" vrnetlab/vr-vmx:15.1F6.9 --trace
```

By default the virtual router runs in standalone mode - a single routing
engine. To change the mode to dual RE, pass `--dual-re` to the launch script.
The second RE console is exposed on port 5001. The management ports (NETCONF,
SSH, SNMP) are exposed on the container IP, offset by 1000.

```
docker run --privileged -d --name vmx15-dual-re vrnetlab/vr-vmx:15.1F6.9 --trace --dual-re
# connect to re0
ssh vrnetlab@$CONTAINER_IP -p 22
# connect to re1
ssh vrnetlab@$CONTAINER_IP -p 1022
```

System requirements
-------------------
CPU: 4 cores - 3 for the vFPC (virtual FPC - the forwarding plane) and 1 for
VCP (the RE / control plane).

RAM: 6GB - 2 for VCP and 4 for vFPC

Disk: ~5GB for JUNOS 15.1, ~7GB for JUNOS 16 (I know, it's huge!!)

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Why use vMX and not VRR?
A: Juniper does indeed publish a VRR image that only requires a single VM to
run, which would decrease the required resources. The vMX VCP (RE / control
plane image) can also be run in the same mode but would then lack certain
forwarding features, notably multicast (which was a dealbreaker for me).
vrnetlab doesn't focus on forwarding performance but the aim is to keep feature
parity with real routers and if you can't test that your PIM neighbors come up
correctly due to lack of multicast then.. well, that's no good.

##### Q: What about licenses?
A: Older vMX in evaluation mode are limited to 30 days and with a throughput
cap of 1Mbps. You can purchase bandwidth licenses to get rid of the time limit
and have a higher throughput cap. vMX 15.1F4 introduced additive bandwidth
licenses which means bandwidth licenses are added together, before which only
the bandwidth license with the highest capacity would be used. In 16.1 the
evaluation period of 30 days was removed to the benefit of a perpetual
evaluation license but still with a global throughput cap of 1Mbps.

##### Q: I'm getting this error: qemu-system-x86_64: /build/qemu-XXUWBP/qemu-2.1+dfsg/hw/usb/dev-storage.c:236: usb_msd_send_status: Assertion `s->csw.sig == cpu_to_le32(0x53425355)' failed.
A: Get a newer kernel & qemu. I've seen this on Ubuntu 15.10. Upgrading to
16.04 fixed it.
