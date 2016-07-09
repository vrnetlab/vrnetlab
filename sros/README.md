vrnetlab / Nokia VSR SROS
=========================
This is the vrnetlab docker image for Nokia VSR / SROS.

Put your sros.qcow2 file in this directory and run `make docker-image` and you
should be good to go. The resulting image is called `vr-sros`. You can tag it
with something else if you want, like `my-repo.example.com/vr-sros` and then
push it to your repo.

This is currently using the "integrated" VSR mode which is single-VM approach.
It works great for testing control plane type of things but the forwarding
plane is lacking a lot of features, most notably CPM filters which means you
can't protect the control plane through policers and whatnot.

Yes, we probably should try to switch to a distributed VSR mode.

Usage
-----
The container must be `--privileged` to start KVM. It needs `--net=host` for
configuring network devices in the main system namespace. In this example we
set the numeric-id to 96 which means the router will get 10.0.0.96/24 and
2001:db8::96/24 configured on its management interface. The management
interface is attached to the Linux bridge called "vr-mgmt", which if it doesn't
exist will be created.
```
docker run -d --privileged --net=host vr-sros --numeric-id 96 --mgmt-bridge vr-mgmt --username Marco --password Polo
```
It takes about 90 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

All the virtual router interfaces are exposed via tap interfaces that are named
based on the numeric-id and the sequence number of the interface. "vr96_00" is
the first interface, "vr96_01" the second and so forth. The first interface
maps to the OOB management port on the router. 

The router is "equipped" with three m20-1gb-xp-sfp MDAs which yields a total of
60 ports although we typically can't expose more than ~30 due to PCI bus
limits. The launch script defaults to 20 NICs. I haven't tested to go beyond
that. The ports are numbered 1/1/[1-20], 1/3/[1-20] and 1/5/[1-20]. Port 1/1/1
corresponds to "vr96_01".

You can connect multiple virtual routers by creating a linux bridge and adding
the interfaces of two routers to that bridge. Here we create a bridge to
connect the first interfaces of vr96 and vr97 with each other:
```
brctl addbr vr96__vr97
brctl addif vr96__vr97 vr96_01
brctl addif vr96__vr97 vr97_01
```

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.
