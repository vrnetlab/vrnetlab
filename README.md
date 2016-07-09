vrnetlab - VR Network Lab
-------------------------
vrnetlab uses docker to help you start virtual routers in a convenient fashion
typically for the purpose of automated CI testing or development environments.

It's been developed at Deutsche Telekom as part of the automated CI test system
for the TeraStream project.

Virtual routers
---------------
There are a number of virtual routers available on the market:

 * Cisco XRv
 * Juniper VRR
 * Juniper vMX
 * Nokia VSR

All of the above are released as a qcow2 or vmdk file (which can easily be
converted into qcow2) making them easy to spin up on a Linux machine. Once spun
up there are a few tasks one normally wants to perform:

 * set an IP address on a management interface
 * start SSH / NETCONF daemon (and generate crypto keys)
 * create initial user so we can login

There might be more things to the list but this is the bare minimum which makes
the router remotely reachable and thus we can configure the rest from the
normal provisioning system.

vrnetlab aims to make this process as simple and convenient as possible so that
it may be used both by humans and automated systems to spin up virtual routers.
In addition, there are scripts to help you generate topologies.

The virtual machines are packaged up in docker container. Since we need to
start KVM and manage network interfaces the docker containers has to be run
with `--privileged` and `--net=host` which effectively defeats the security
features of docker. Our use of docker is essentially reduced to being a
packaging format but a rather good one at that.

It's possible to remotely control a docker engine and tell it to start/stop
containers. It's not entirely uncommon to run the CI system in a VM and letting
it remotely control another docker engine can give us some flexibility in where
the CI runner is executed vs where the virtual routers are running.

libvirt can also be remotely controlled so it could potentially be used to the
same effect. However, unlike libvirt, docker also has a registry concept which
greatly simplifies the distribution of the virtual routers. It's already neatly
packaged up into a container image and now we can pull that image through a
single command. With libvirt we would need to distribute the VM image and
launch scripts as individual files.

The launch script differ from router to router. For example, it's possible to
feed a Cisco XR router a bootup config via a virtual CD-ROM drive so we can use
that to enable SSH/NETCONF and create a user. Nokia VSR however does not, so we
need to tell KVM to emulate a serial device and then have the launch script
access that virtual serial port via telnet to do the initial config.

The intention is to keep the arguments to each virtual router type as similar
as possible so that a test orchestrator or similar need minimal knowledge about
the different router types.

FAQ
---
##### Q: Why don't you ship pre-built docker images?
A: I don't think Cisco, Juniper or Nokia would allow me to ship their virtual
   router images so you just have to build the docker images yourself.

##### Q: Why don't you ship docker images where I can provide the image through a volume?
A: I don't like the concept as it means you have to ship around an extra file.
   If it's a self-contained image then all you have to do is push it to your
   docker registry and then ask a box in your swarm cluster to spin it up!
