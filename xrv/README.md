vrnetlab / Cisco IOS XRv
========================
This is the vrnetlab docker image for Cisco IOS XRv.

Building the docker image
-------------------------
Download IOS XRv from
https://upload.cisco.com/cgi-bin/swc/fileexg/main.cgi?CONTYPES=Cisco-IOS-XRv
Put the .vmdk file in this directory and run `make docker-image` and you
should be good to go. The resulting image is called `vr-xrv`. You can tag it
with something else if you want, like `my-repo.example.com/vr-xrv` and then
push it to your repo.

Usage
-----
The container must be `--privileged` to start KVM. It needs `--net=host` for
configuring network devices in the main system namespace. In this example we
set the numeric-id to 96 which means the router will get 10.0.0.96/24 and
2001:db8::96/24 configured on its management interface. The management
interface is attached to the Linux bridge called "vr-mgmt", which if it doesn't
exist will be created.
```
docker run -d --privileged --net=host vr-xrv --numeric-id 96 --mgmt-bridge vr-mgmt --username Marco --password Polo
```
It takes about 150 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.
