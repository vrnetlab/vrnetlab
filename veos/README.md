vrnetlab / Arista vEOS
======================
This is the vrnetlab docker image for Arista vEOS.


Building the docker image
-------------------------
Download vEOS in vmdk format and the Aboot file from 
https://www.arista.com/en/support/software-download
Make sure you grab the Aboot file with 'serial' in the name, like
Aboot-veos-serial-8.0.0.iso. Place both the Aboot iso and the .vmdk file in
this directory and run make. The resulting images is called `vr-veos`. You can
tag it with something else if you want, like `my-repo.example.com/vr-veos` and
then push it to your repo. The tag is the same as the version of the vEOS
image, so if you have vEOS-lab-4.16.6M.vmdk your final docker image will be
called vr-veos:4.16.6M


Usage
-----
```
docker run -d --privileged --name my-veos-router vr-veos
```

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
