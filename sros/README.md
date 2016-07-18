vrnetlab / Nokia VSR SROS
=========================
This is the vrnetlab docker image for Nokia VSR / SROS.

Ask your Nokia representative for the VSR image.  Put the sros.qcow2 file in
this directory and run `make docker-image` and you should be good to go. The
resulting image is called `vr-sros`. You can tag it with something else if you
want, like `my-repo.example.com/vr-sros` and then push it to your repo.

This is currently using the "integrated" VSR mode which is single-VM approach.
It works great for testing control plane type of things but the forwarding
plane is lacking a lot of features, most notably CPM filters which means you
can't protect the control plane through policers and whatnot.

Yes, we probably should try to switch to a distributed VSR mode.

It's been tested to at least boot with:

 * 12.0.R6

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-sros-router vr-sros
```
It takes about 90 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

The router is "equipped" with three m20-1gb-xp-sfp MDAs which yields a total of
60 ports although we typically can't expose more than ~30 due to PCI bus
limits. The launch script defaults to 20 NICs. I haven't tested to go beyond
that. The ports are numbered 1/1/[1-20], 1/3/[1-20] and 1/5/[1-20].

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.
