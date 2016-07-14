vrnetlab / Cisco IOS XRv
========================
This is the vrnetlab docker image for Cisco IOS XRv.

Building the docker image
-------------------------
Put the XRV .qcow2 file in this directory and run `make docker-image` and you
should be good to go. The resulting image is called `vr-xrv`. You can tag it
with something else if you want, like `my-repo.example.com/vr-xrv` and then
push it to your repo.
