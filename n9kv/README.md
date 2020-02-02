vrnetlab / Cisco Nexus 9000v
===========================
This is the vrnetlab docker image for Cisco Nexus NXOS 9000v virtual switch.

Building the docker image
-------------------------
Put the .qcow2 file in this directory and run `make docker-image` and
you should be good to go. The resulting image is called `vr-nxos`. You can tag
it with something else if you want, like `my-repo.example.com/vr-nxos` and then
push it to your repo. The tag is the same as the version of the NXOS image, so
if you have nxosv.9.2.4.qcow2 your final docker image will be called
vr-nxos:9.2.4

Usage
-----
```
docker run -d --privileged --name my-nxos-router vr-nxos
```

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Sorta. This is being used for testing some things with netmiko and ssh2net.
