vrnetlab / Cisco Catalyst 8000v
===========================
This is the vrnetlab docker image for Cisco Catalyst 8000v. The device may be
used in two modes:
- regular,
- SD-WAN Controller mode (managed by Viptela).

The Catalyst 8000v platform is a successor to the CSR 1000v. This image was
split off because to enable the Controller mode you have to effectively boot the
router into a completely different mode. In the near future there will be a
single 'cat8000v' platform that will produce both the regular and sd-wan images.

Building the docker image
-------------------------
Put the .qcow2 file in this directory and run `make docker-image` and
you should be good to go. The resulting image is called `vr-cat8000v-sd-wan`. You can tag
it with something else if you want, like `my-repo.example.com/vr-cat8000v-sd-wan` and then
push it to your repo. The tag is the same as the version of the CSR image, so
if you have csr1000v-universalk9.17.03.01a.qcow2 your final docker image will be called
vr-cat8000v-sd-wan:17.03.01a

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to boot and respond to SSH with:

 * 17.03.01a (csr1000v-universalk9.17.03.01a.qcow2)

Usage
-----
```
docker run -d --privileged --name my-csr-router vr-cat8000v-sd-wan
```

System requirements
-------------------
CPU: 1 core

RAM: 4GB

Disk: <500MB

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. 
