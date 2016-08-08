vrnetlab / Cisco Nexus NXOS
===========================
This is the vrnetlab docker image for Cisco Nexus NXOS Titanium emulator.

Building the docker image
-------------------------
Titanium doesn't appear to be exactly official but you can get it from the
Internet. VIRL is said to include it, so you may have luck in extracting it
from there.

Anyway, put the .qcow2 file in this directory and run `make docker-image` and
you should be good to go. The resulting image is called `vr-nxos`. You can tag
it with something else if you want, like `my-repo.example.com/vr-nxos` and then
push it to your repo. The tag is the same as the version of the NXOS image, so
if you have nxosv-7.2.0.D1.1.qcow2 your final docker image will be called
vr-nxos:7.2.0.D1.1

Usage
-----
```
docker run -d --privileged --name my-nxos-router vr-nxos
```

System requirements
-------------------
CPU: 1 core

RAM: 2GB

Disk: <500MB


FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. I don't use Nexus myself (yet) so not much testing at all really.
Please do try it out and let me know if it works.
