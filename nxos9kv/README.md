vrnetlab / Cisco NX-OSv 9000
============================
This is the vrnetlab docker image for Cisco NX-OSv 9000 Virtual Switch.

Building the docker image
-------------------------
This is the officially supported image and is different from the Titanium
emulator. The image can be downloaded directly from Cisco site.

Additional files needed
-----------------------
You need to download the nexus9x00v image from Cisco. You will also need to
download the EFI boot image, such as the one from 
https://www.kraxel.org/repos/jenkins/edk2. You need to extract the 
OVMF-pure-efi.fd file from the RPM package, this EFI boot image is used to
boot up the nexus9x00v image.

Anyway, put the .qcow2 and the fd files in this directory and run 
`make docker-image` and you should be good to go. The resulting image
is called `vr-nxos9k`. You can tag it with something else if you want,
like `my-repo.example.com/vr-nxos9k` and then push it to your repo. The tag
is the same as the version of the NXOS image, so if you have
nexus9300v.9.3.7.qcow2 your final docker image will be called vr-nxos:9.3.7.

Usage
-----
```
docker run -d --privileged --name my-nxos-router vr-nxos9k:9.3.7
```
You may specify the number of NICs with --num-nics, the default is 24 with a
maximum of 65 for 9300v.

Initial Configuration
---------------------
The initial configuration file called nxos_config.txt is required. This file
should contain some minimal configuration. A sample configuration is included.

System requirements
-------------------

Currently there are two platforms, 9300v and 9500v. If you are using vrnetlab
I assume you want the light weight 9300v. The resource requirement is based on
9300v.

CPU: 1 core, 2 prefered, the VR is not stable in my tests with 1 core.

RAM: 8GB, Cisco recommends 4GB, but in my case 4GB is not enough.

Disk: 8GB

I only tested with 9300v.

Known issues
------------
It is known that a previously booted image may not start properly. We have
implemented a check that once a container stops then restarts, all its
configurations (stored in the overlay image) are wiped clean before running.
You will have to configure from scratch for each run.

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Only basic configuration by the author on Ubuntu 20.04 server running Intel
Xeon chips, both CLI and Netconf work. Layer2/layer3 functions are not tested.
