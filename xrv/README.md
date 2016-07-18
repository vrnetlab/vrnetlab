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

This is not tested with XRv9000, which has a different dataplane and
potentially different setup/boot mechanics.

It's been tested to at least boot with:

 * 5.3.3.51U (TeraStream build but 5.3 is prolly fine)

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-xrv-router vr-xrv
```
It takes about 150 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.
