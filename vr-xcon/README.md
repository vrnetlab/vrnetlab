vrnetlab xcon
=============
This is the vrnetlab docker image of xcon - the cross-connect app.

vr-xcon is used to connect two or more vrnetlab containers with each other.

Modes of operation
------------------

### TcpBridge
All vrnetlab routers are run by qemu which expose the router interfaces via TCP
ports and vr-xcon connects these together. It can be seen as an overlay. The
underlying TCP ports exposed by qemu listen on the docker0 interface (per
default) of each container but as long as two vrnetlab containers have
connectivity via their default network, vr-xcon should be able to perform it's
job.

### Tcp2Tap
vr-xcon also provides a mode to interconnect the TCP-socket exposed by qemu to
a local tap interface, which makes it easy to use other apps together with
vrnetlab router containers. Run vr-xcon with `--tap-listen INTERFACE` to listen
to a port - the mapping is the same as for other vrnetlab routers, i.e.
INTERFACE=1 will mean it listens on TCP port 10001 and this makes it easy to
interconnect using vr-xcon. See vr-bgp for an example of how `--tap-listen` can
be used in real life.

In this mode, vr-xcon can also be used to configure IP addressing of the local
tap interface. This includes setting an IPv4/IPv6 address, default route and VLAN ID.

Building the docker image
-------------------------
The vr-xcon container image is available from Docker Hub as vrnetlab/vr-xcon,
so unless you have done local modifications, there is no real need to build
your own container.

Nevertheless, run `make` to build your own container image. The resulting image
will be called 'vr-xcon'. The environment variable REGISTRY can be set to give
the resulting image a prefix, for example by setting registry to
'registry.example.com:1234' the resulting image will be called
'registry.example.com:1234/vr-xcon' and can then be pushed to the registry
through `docker push`.

Usage
-----

### TcpBridge mode
To connect the first interface of vr1 and vr2 and the second interface of vr1
with the first of vr3, run:
```
docker run -d --privileged --name vr-xcon --link vr1 --link vr2 --link vr3 vr-xcon --p2p vr1/1--vr2/1 vr1/2--vr3/1
```
Note how --p2p is not repeated and the arguments to it are simply appended.

Tcp2Bridge mode also supports tagging/stripping VLANs from packets. Lets say vr1 
sends packets tagged with vlan-id 123, but you would like to forward them to vr2
untagged (to simplify test environment for example) you can do this with:

```
docker run -d --privileged --name vr-xcon --link vr1 --link vr2 --p2p vr1/1--vr2/1:123
```

Packets from vr1  to vr2 without vlan-id 123 will be discarded, while traffic going from vr2
towards vr1 will be tagged with vlan-id 123. It is possible to specify vlan-id also on 
the other side of the link:

```
docker run -d --privileged --name vr-xcon --link vr1 --link vr2 --p2p vr1/1:123--vr2/1
```

Note that having vlan tag on both sides (changing vlan-id) is not supported. 

It's possible to use the `--debug` option to have a debug written out for every
packet.

### Tcp2Tap mode
For example, say we have a virtual router _r1_, and  want to connect an application
running in the _app_ docker container to the overlay network. We will need to run vr-xcon
in the _app_ container in _Tcp2Tap_ mode, and then connect the two containers with
vr-xcon in _TcpBridge_ mode.

The _r1_ interface already has IPv6 address 2003:1c08:161:1ff::1, we want our app to
use 2003:1c08:161:1ff::42 and also use _r1_ as the default gateway to access the rest
of the overlay networks.

First, run vr-xcon in the _app_ container in the background (note this assumes the
`app` container runs in _privileged_ mode):
```
docker exec -d app bash -c "/xcon.py --tap-listen 1 --ipv6-address 2003:1c08:161:1ff::42/64 --ipv6-route 2003:1c08:161:1ff::1"
```

Then, connect the _app_ container with _r1_ using vr-xcon in _TcpBridge_ mode:
```
docker run -d --privileged --name vr-xcon --link r1 --link app vr-xcon --p2p r1/1--app/1
```

Experimental xcon-ng (acton)
----------------------------
An alternative implementation of xcon written in acton
(https://www.acton-lang.org/) is currently in development. Currently it only
supports TcpBridge mode but the argument format is equivalent. To use it just
replace the entrypoint with `--entrypoint /xcon`.

```
docker run -d --privileged --name vr-xcon-ng --entrypoint /xcon --link vr1 --link vr2 --link vr3 vr-xcon --p2p vr1/1--vr2/1 vr1/2--vr3/1
```

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Can I use '--' in the names of my vrnetlab containers?
A: No, since -- is used as the separator in the --p2p argument list for
separating two vrnetlab instances you can not use -- in the name of the
container itself.

##### Q: Is this fast?
A: I haven't tested but I would assume it is incredibly slow.

##### Q: What about jitter / PDV (packet delay variation)?
A: Hehe, it can be really bad:

    64 bytes from 192.168.1.2: icmp_seq=2097 ttl=64 time=4.769 ms
    64 bytes from 192.168.1.2: icmp_seq=2098 ttl=64 time=8.317 ms
    64 bytes from 192.168.1.2: icmp_seq=2099 ttl=64 time=15.112 ms
    64 bytes from 192.168.1.2: icmp_seq=2100 ttl=64 time=38.859 ms
    64 bytes from 192.168.1.2: icmp_seq=2101 ttl=64 time=1.940 ms

UPDATE: Most packet delay variation seem to stem from the routers themselves.
Different routers induce different amounts of PDV.

##### Q: Why not connect virtual routers via tap interfaces?
A: It would require fiddling lots more with kernel level networking, which
isn't fun in a docker environment. Since the TCP packets encapsulating the
inner payload run on top of the docker0 bridge it's actually possible to run
vrnetlab virtual routers on different docker hosts and use docker overlay
networking to connect these together (although I've never tested). That
wouldn't work with kernel tap interfaces or similar.

##### Q: Why not use normal docker networks?
A: Docker isn't really built for network centric applications. The default
networking provides a single interface to the container and adding more is a
somewhat elaborate process. In addition, it appears that the networking needs
to be setup before the container starts, which is a no-go for vrnetlab as one
of the design criterias is to be able to setup the topology, or modify it,
after the containers have been started.

##### Q: Why not use TCP listen & connect mode directly from qemu?
A: While this would get rid of vr-xcon and potentially perform much much
better it means the topology would have to be known ahead of time and you
couldn't do any changes to the topology while the virtual routers are running.
vr-xcon defines the topology after the fact that the virtual routes have been
started, making it possible to change the topology by stopping vr-xcon and
starting a new one with a new topology.

##### Q: Starting and stopping vr-xcon to build a new topology would mean packet loss, no?
A: Yes indeed, it will very likely induce packet loss. I believe it could be
kept relatively short though and the way qemu works the virtual routers would
never see their interfaces go down so IS-IS, OSPF or similar should stay up. If
I were to take a guess I think vr-xcon could be stopped and started within a
few milliseconds, so even BFD could potentially be run with quite aggressive
timers without a problem.

Additionally, one can use one vr-xcon process/container per link such that it
is possible to stop a single vr-xcon process without affecting other links.

##### Q: Why not use UDP mode as provided by qemu to directly connect the router?
A: UDP could indeed be used and there would be two alternatives to this, one
would be to set UDP src/dst pairs so that the qemu processes would talk
directly to each other, this however has the inherent problem of knowing the
topology ahead of time. See a previous answer on why this is bad.

The other option would be to use "generic" UDP src/dst pairs and we could have
a udpbridge that receives packets from the virtual routers and virtually
cross-connects them to each other. This is virtually the same as the current
vr-xcon concept, just using UDP instead of TCP but it would also require one
end to be known, which brings us back to the problem of knowing the topology
before the containers are started.
