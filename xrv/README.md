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
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-xrv-router vr-xrv
```
It takes about 150 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.
