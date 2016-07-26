vrnetlab / Juniper vMX
========================
This is the vrnetlab docker image for Juniper vMX.

Building the docker image
-------------------------
Download vMX from http://www.juniper.net/support/downloads/?p=vmx#sw
Put the .tgz file in this directory and run `make` and you should be good to
go. The resulting image is called `vr-vmx`. You can tag it with something else
if you want, like `my-repo.example.com/vr-vmx` and then push it to your repo.
The tag is the same as the version of the JUNOS image, so if you have
vmx-15.1F4.15.tgz your final docker image will be called vr-vmx:15.1F4.15.

It's been tested to boot and respond to SSH with:

 * 15.1F6.9 (vmx-bundle-15.1F6.9.tgz)
 * 16.1R1.7 (vmx-bundle-16.1R1.7.tgz)

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-vmx-router vr-vmx
```
It takes about TBD seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.

The vFPC has a serial port that is exposed on TCP port 5001. Normally you don't
need to interact with it but I imagine it could be useful for some debugging.

System requirements
-------------------
CPU: 5 cores - 4 for the vFPC (virtual FPC - the forwarding plane) and 1 for
VCP (the RE / control plane).

RAM: 8GB - 4 for VCP and 4 for vFPC

Disk: ~5GB for JUNOS 15.1

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
licenses, before which only the bandwidth license with the highest capacity
would be used. In 16.1 the evaluation period of 30 days was removed to the
benefit of a perpetual evaluation license but still with a global throughput
cap of 1Mbps.
