vrnetlab / Arista vEOS
======================
This is the vrnetlab docker image for Arista vEOS.

Building the docker image
-------------------------
Download vEOS in vmdk format and the Aboot file from 
https://www.arista.com/en/support/software-download
Make sure you grab the Aboot file with 'serial' in the name, like
Aboot-veos-serial-8.0.0.iso. You should get the vmdk filed starting with
vEOS-lab-... do not use the "-combined" image, as it combines a vmdk with the
Aboot without serial support. Place both the Aboot iso and the .vmdk file in
this directory and run make. The resulting images is called `vr-veos`. You can
tag it with something else if you want, like `my-repo.example.com/vr-veos` and
then push it to your repo. The tag is the same as the version of the vEOS
image, so if you have vEOS-lab-4.16.6M.vmdk your final docker image will be
called vr-veos:4.16.6M

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to boot, respond to SSH and have correct interface mapping
with the following images:

 * vEOS-lab-4.16.6M.vmdk  MD5:b3f7b7cee17f2e66bb38b453a4939fef

It defaults to 144 NICs (3x48 port line cards).

Usage
-----
```
docker run -d --privileged --name my-veos-router vr-veos
```

Starting vEOS can easily take more than 10 minutes to start; be patient.

You can use --trace on the docker image to see boot output.

System requirements
-------------------
CPU: 1 core

RAM: 2GB

Disk: <1GB


FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. I don't use Arista gear myself (yet) so not much testing at all
really.  Please do try it out and let me know if it works.
