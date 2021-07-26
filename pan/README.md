# pan / PA-VM

This is the vrnetlab docker image for Palo Alto PA-VM firewalls.


## Building the docker image

Download PA-VM in KVM/qcow2 format from the Palo Alto website (you will need a login/access).
Place the .qcow2 file in this directory and run make. The resulting images is called `vrnetlab/vr-pan:VERSION`. You can
tag it with something else if you want, like `my-repo.example.com/vr-pan` and
then push it to your repo. 

It's been tested to boot, respond to SSH and have correct interface mapping
with the following images:

 * PA-VNM-KVM-7.0.1.qcow2
 * PA-VNM-KVM-9.1.9.qcow2
 * PA-VNM-KVM-10.0.6.qcow2


## System requirements

* CPU: 2 core
* RAM: 6GB
* Disk: <1GB

