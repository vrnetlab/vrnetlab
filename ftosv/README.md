# Dell FTOSv (OS10) / ftosv

This is the vrnetlab docker image for Dell FTOS10 virtual switch.


## Building the docker image

Put the .qcow2 file in this directory and run make docker-image and you should be good to go. The resulting image is 
called vr-ftosv. You can tag it with something else if you want, like my-repo.example.com/vr-ftosv and then push it to 
your repo. The tag is the same as the version of the FTOS image, so if you have dellftos.10.5.2.4.qcow2 your final docker 
image will be called vr-ftosv:10.5.2.4

NOTE:
* Dell officially does not provide .qcow2 disk images. Check Dell OS10 virtualization documentation on how to prepare disk image from officially available virtualization package. One can use either GNS3 or EVE-NG to prepare .qcow2 disk.
* Number of interfaces are dependent on FTOS platform used in .qcow2 disk. By default, number of interfaces set under `launch.py` is `56` based on S5248 platform.

## System requirements

* CPU: 4 core
* RAM: 4GB
* Disk: <5GB

