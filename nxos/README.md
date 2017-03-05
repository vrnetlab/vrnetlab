vrnetlab / Cisco Nexus NXOS
===========================
This is the vrnetlab docker image for Cisco Nexus NXOS 9000v and the NXOS
Titanium emulator.

Building the docker image
-------------------------
First off, there seems to be kind of two versions of a virtual Nexus. There's a
NXOS 9000v image available from Cisco CCO and it appears to be rather official,
let's call it 'final'. Long before this final image was made available for
download there was a "Titanium" emulator that could be used. The emulator
appears to be much less official although VIRL is said to have included it (you
might have luck extracting it from VIRL). As always, it can be found on the
Internet.

Anyway, put the .qcow2 file in this directory and run `make docker-image` and
you should be good to go. The resulting image is called `vr-nxos`. You can tag
it with something else if you want, like `my-repo.example.com/vr-nxos` and then
push it to your repo. The tag is the same as the version of the NXOS image, so
if you have nxosv-7.2.0.D1.1.qcow2 your final docker image will be called
vr-nxos:7.2.0.D1.1

Tested with:
 * nxosv-7.2.0.D1.1.qcow2  MD5:0ee38c7d717840cb4ca822f4870671d0
 * nxosv-final.7.0.3.I5.1.qcow2  MD5:201ea658fa4c57452ee4b2aa4f5262a7

nxosv-final.7.0.3.I5.1.qcow2 is an official image from Cisco while I think
nxosv-7.2.0.D1.1.qcow2 is one of these less official Titanium emulators.

Usage
-----
```
docker run -d --privileged --name my-nxos-router vr-nxos
```

System requirements
-------------------
CPU: 1 core

RAM: 2GB (titanium) or 8GB (final)

Disk: <500MB


FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. I don't use Nexus myself (yet) so not much testing at all really.
Please do try it out and let me know if it works.
