tcpbridge
=========
This is the vrnetlab docker image of tcpbridge.

tcpbridge is used to connect two or more vrnetlab containers with each other.
All vrnetlab routers are run by qemu which expose the router interfaces via TCP
ports and tcpbridge connects these together, thus the name.


Building the docker image
-------------------------
Run `make`.

Usage
-----
To connect the first interface of vr1 and vr2, run:
```
docker run -d --privileged --name tcpbridge --link vr1 --link vr2 tcpbridge --p2p vr1/1--vr2/1
```

It's possible to use the `--debug` option to have a debug written out for every
packet.

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Is this fast?
A: I haven't tested but I would assume it is incredibly slow.

##### Q: What about jitter / PDV (packet delay variation)?
A: Hehe, it can be really bad:

    64 bytes from 192.168.1.2: icmp_seq=2097 ttl=64 time=4.769 ms
    64 bytes from 192.168.1.2: icmp_seq=2098 ttl=64 time=8.317 ms
    64 bytes from 192.168.1.2: icmp_seq=2099 ttl=64 time=15.112 ms
    64 bytes from 192.168.1.2: icmp_seq=2100 ttl=64 time=38.859 ms
    64 bytes from 192.168.1.2: icmp_seq=2101 ttl=64 time=1.940 ms

##### Q: Why not connect virtual routers via tap interfaces?
A: It would require fiddling lots more with kernel level networking, which
isn't fun in a docker environment. Since the TCP packets encapsulating the
inner payload run on top of the docker0 bridge it's actually possible to run
vrnetlab virtual routers on different docker hosts and use docker overlay
networking to connect these together (although I've never tested). That
wouldn't work with kernel tap interfaces or similar.

##### Q: Why not use TCP listen & connect mode directly from qemu?
A: While this would get rid of tcpbridge and potentially perform much much
better it means the topology would have to be known ahead of time and you
couldn't do any changes to the topology while the virtual routers are running.
tcpbridge defines the topology after the fact that the virtual routes have been
started, making it possible to change the topology by stopping tcpbridge and
starting a new one with a new topology.

##### Q: Starting and stopping tcpbridge to build a new topology would mean packet loss, no?
A: Yes indeed, it will very likely induce packet loss. I believe it could be
kept relatively short though and the way qemu works the virtual routers would
never see their interfaces go down so IS-IS, OSPF or similar should stay up. If
I were to take a guess I think tcpbridge could be stopped and started within a
few milliseconds, so even BFD could potentially be run with quite aggressive
timers without a problem.

##### Q: Why not use UDP mode as provided by qemu to directly connect the router?
A: UDP could indeed be used and there would be two alternatives to this, one
would be to set UDP src/dst pairs so that the qemu processes would talk
directly to each other, this however has the inherent problem of knowing the
topology ahead of time. See a previous answer on why this is bad.

The other option would be to use "generic" UDP src/dst pairs and we could have
a udpbridge that receives packets from the virtual routers and virtually
cross-connects them to each other. This is virtually the same as the current
tcpbridge concept, just using UDP instead of TCP. I'm not sure what is best.
TCP won't drop packets but UDP could potentially lower latency by not requiring
ordering of packets.
