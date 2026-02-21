vrnetlab topology machine
=========================
The topology machine will help you manage a topology of virtual routers.

In particular, there are two activites related to building a topology that can
be really tedious and topology machine is meant to help you with these:

 * building a full-mesh
 * assigning interfaces to point-to-point links between routers

Full-meshes defined in the configuration file will be expanded into
point-to-point links between all the member routers.

Each point-to-point link needs to have an interface assigned on the routers on
the respective ends of the link. Once you have more than a handful of links it
can become really tedious to sort out what goes where and any additions or
deletions to your topology means instant headache... which is where topo
machine comes in.

You write a high level topology definition which topology machine can convert
into a low level topology definition through --build:
```
topo --build hltopo.json > lltopo.json
```
The output is printed to stdout so you can view it, pipe or redirect to a file
if you want. You only need to run the build the low level topology from the
high level topology once. All subsequent use of --run, --template or similar
uses that one resulting low level topology. Naturally, if you update the high
level topology you must rerun the --build topology to update the low level
topology.

topomachine does not currently use any information from the low level topology
(produced during a previous --build operation) which means that removing a link
will very likely result in changes to the majority of links in the topology as
they will be re-assigned to new interfaces.

The default behavior is to sort the routers and links and assign interfaces
numbers to links in this sorted order. There is however an option called
`--keep-order` that will take into account the order in which the *p2p* links
and routers in *fullmeshes* are defined in the configuration file. This makes
the interface assignment more stable when changing the topology. It also makes
the assignment more natural, as we tend to list the important routers (like PE
routers) in the topology first, followed by CPEs and the like. The interfaces on
the devices listed first will be assigned lower numbers. As a last resort when
you really really need to use a specific interface for a link, you can assign a
static numeric interface ID in the *p2p* section of the topology file.

topology machine is able to run the machines for you, i.e. execute docker run
for the routers defined in the configuration file and start vr-xcon with the
relevant arguments to complete the topology:
```
topo --run lltopo.json
```
which will then start the docker containers based on the computed topology.
There's a --dry-run option if you just want to see what commands would be
executed. If you want to run multiple topologies at the same time you can
specify a prefix for the docker container names using `--prefix` which prevents
collisions if you use the same name for the virtual routers in the different
topology configurations. Note how 

Last but not least, there is a template mode which you can use to produce
configuration for your mangement system, which in turn is provisioning the
routers. Since the provisioned configuration of the virtual routers needs to
align with the "physical" topology built by vr-xcon it makes sense to let
topology machine assist you in producing this service config.

Use `--template` to produce output based on the provided topology information
and template:
```
topo --template lltopo.json my-template.template
```
Output is printed to stdout which can redirected to a file. Jinja2 is used as
the templating language. See example-template.template for how a config to a
network provisioning system can be produced. It has the notion of a
"base-config" applies common configuration to a device and the
"backbone-interface" service which configures an interface on a router for
backbone use.


Configuration file format
-------------------------
Feed it a config file in JSON format. There are three parts of the
configuration file:

 * routers
 * p2p
 * fullmeshes

All of which are demonstrated in the accompanying example-topology.json file.

Configuration section "routers"
-------------------------------
The routers section is a declaration of the routers in your topology. You need
to fill in the type and version, which should match up with the vrnetlab
routers you have available, e.g. if you have vr-xrv:5.3.3 you fill in type
"xrv" and version "5.3.3". It's important for topo builder to know about the
router type as it will later map interface to interface names like
GigabitEthernet0/0/0/0 or ge-0/0/0 depending on router type.

```
{
	"routers": {
		"a-pe-router-1": { "type": "xrv", "version": "5.3.3" }
	}
}
```

Any other keys filled in will be transparently passed through topology machine,
which can be very useful for adding extra information for use with the
`--template` option.

Configuration section "p2p"
---------------------------
"p2p" is the second section in the config file and you can use this to define
point-to-point links. Each entry is keyed by the left side of the link followed
by an array of the routers to add a link to.

NOTE: The ends of each link are referred to as "left" and "right". There's no
real importance in the naming - we just needed to call each end something.

For example:

```
{
	"p2p": {
		"foo": [ "a", "b", "c" ]
	}
}
```

The above config will generate three links:

 * foo <-> a
 * foo <-> b
 * foo <-> c

It's also possible to add multiple links to the same router simply by adding a
router twice:

```
{
	"p2p": {
		"foo": [ "a", "a" ]
	}
}
```

 * foo <-> a
 * foo <-> a

The array of routers on the right side may also include static interface
assignment. Use the a dict to assign a specific interface to a link. For
example:

```
{
    "p2p": {
        "foo": [ "a", {"router": b, "numeric": 42} ]
    }
}
```

 * foo <-> a/1
 * foo <-> b/2

 Another option is to have links where you want to emulate an access switch
 between the two endpoints. 802.1q VLAN tags will be automatically stripped from
 the frames sent from the left side to the right side. And conversely, the right
 side is expected to send untagged frames which are then tagged before being
 sent to the left side. For example:

 ```
 "p2p": {
        "foo": [ "b", {"router": "b", "vlan": 123}, {"router": "b", "vlan": 456}]
    }
 ```

 Generated links:

 * foo <-> b with untagged traffic
 * foo <-> b:123 where foo is sending tagged traffic with vlan 123 and b receives untagged traffic.
 * foo <-> b:456 where foo is sending tagged traffic with vlan 456 and b receives untagged traffic.
 
Configuration section "fullmeshes"
----------------------------------
Last but not least we have the fullmeshes section which helps you build one or
more fullmeshes. Name your fullmesh something and list the members:

```
{
	"fullmeshes": {
		"sweden": [ "gothenburg", "stockholm", "malmo" ]
	}
}
```
Note how it's possible to create multiple full-meshes:
```
{
	"fullmeshes": {
		"sweden": [ "gothenburg", "stockholm", "malmo" ],
		"germany": [ "frankfurt", "berlin", "hamburg" ]
	}
}
```

Build as a docker container
---------------------------
You can build topomachine as a docker container for easy distribution.

```
$ cd topology-machine
$ make
```

And you should now have a docker container named topomachine

Use docker container
--------------------
The topomachine docker container can be used to generate the low level topology 
(--build), to generate the docker run commands (--dry-run), to start the 
topology (--run), and to generate custom output using a jinja2 template 
(--template).

The topomachine binary is placed in `/usr/local/bin/topomachine` and is also set
as an *ENTRYPOINT* for the container. The *WORKDIR* is set to `/data` so you can
bind mount a host directory to `/data` and use `docker run ...` as a drop-in
replacement for the topomachine command.

For example:

generate the low level topology:
```
$ docker run -t -v $(pwd):/data topomachine --build example-hltopo.json > example-lltopo.json
```

generate the docker run commands:
```
$ docker run -v $(pwd):/data topomachine --run example-lltopo.json --dry-run
The following commands would be executed:
docker run --privileged -d --name ams-core-1 vrnetlab/vr-xrv:5.1.1.54U --foo bar 1
docker run --privileged -d --name ams-core-2 vrnetlab/vr-xrv:5.1.1.54U --foo bar 1
docker run --privileged -d --name ams-edge-1 vrnetlab/vr-xrv:5.1.1.54U
docker run --privileged -d --name fra-core-1 vrnetlab/vr-vmx:16.1R1.7 --foo ['bar', 1]
docker run --privileged -d --name fra-core-2 vrnetlab/vr-vmx:16.1R1.7
docker run --privileged -d --name fra-edge-1 vrnetlab/vr-vmx:16.1R1.7
docker run --privileged -d --name kul-core-1 vrnetlab/vr-xrv:5.1.1.54U
docker run --privileged -d --name par-core-1 vrnetlab/vr-sros:13.0.B1-4281
docker run --privileged -d --name par-core-2 vrnetlab/vr-sros:13.0.B1-4281
docker run --privileged -d --name par-edge-1 vrnetlab/vr-sros:13.0.B1-4281
docker run --privileged -d --name png-edge-1 vrnetlab/vr-xrv:5.1.1.54U
docker run --privileged -d --name sgp-core-1 vrnetlab/vr-xrv:5.1.1.54U
docker run --rm --privileged -d --name vr-xcon --link ams-core-1:ams-core-1 --link ams-core-2:ams-core-2 --link ams-edge-1:ams-edge-1 --link fra-core-1:fra-core-1 --link fra-core-2:fra-core-2 --link fra-edge-1:fra-edge-1 --link kul-core-1:kul-core-1 --link par-core-1:par-core-1 --link par-core-2:par-core-2 --link par-edge-1:par-edge-1 --link png-edge-1:png-edge-1 --link sgp-core-1:sgp-core-1 vrnetlab/vr-xcon --p2p ams-edge-1/1--ams-core-1/1 ams-edge-1/2--ams-core-2/1 fra-core-2/1--sgp-core-1/1 fra-core-2/2--kul-core-1/1 fra-edge-1/1--fra-core-1/1 fra-edge-1/2--fra-core-2/3 par-core-1/1--sgp-core-1/2 par-core-1/2--kul-core-1/2 par-edge-1/1--par-core-1/3 par-edge-1/2--par-core-2/1 png-edge-1/1--sgp-core-1/3 png-edge-1/2--kul-core-1/3 kul-core-1/4--sgp-core-1/4 ams-core-1/2--ams-core-2/2 ams-core-1/3--fra-core-1/2 ams-core-1/4--fra-core-2/4 ams-core-1/5--par-core-1/4 ams-core-1/6--par-core-2/2 ams-core-2/3--fra-core-1/3 ams-core-2/4--fra-core-2/5 ams-core-2/5--par-core-1/5 ams-core-2/6--par-core-2/3 fra-core-1/4--fra-core-2/6 fra-core-1/5--par-core-1/6 fra-core-1/6--par-core-2/4 fra-core-2/7--par-core-1/7 fra-core-2/8--par-core-2/5 par-core-1/8--par-core-2/6
docker run --privileged -d --name vr-xcon-hub-ams-mgmt --link ams-core-1:ams-core-1 --link ams-core-2:ams-core-2 --link ams-edge-1:ams-edge-1 --link fra-core-1:fra-core-1 --link fra-core-2:fra-core-2 --link fra-edge-1:fra-edge-1 --link kul-core-1:kul-core-1 --link par-core-1:par-core-1 --link par-core-2:par-core-2 --link par-edge-1:par-edge-1 --link png-edge-1:png-edge-1 --link sgp-core-1:sgp-core-1 vrnetlab/vr-xcon --hub ams-core-1/7 ams-core-2/7 ams-edge-1/3
```

To start the topology, topomachine needs access to the docker socket. Add the
`-v /var/run/docker.sock:/var/run/docker.sock` option to the `docker run ...`:
```
$ docker run -v $(pwd):/data -v /var/run/docker.sock:/var/run/docker.sock topomachine --run example-lltopo.json
```

generate custom output using a jinja2 template:
```
$ docker run -t -v $(pwd):/data topomachine --template example-lltopo.json example.template
infrastructure {
    base-config fra-edge-1 {
        numeric-id 101;
		ipv4-address 10.0.0.101;
		ipv6-address 2001:db8::101;
    }
    base-config fra-core-2 {
        numeric-id 4;
		ipv4-address 10.0.0.4;
		ipv6-address 2001:db8::4;
    }
...
    backbone-interface par-core-1 2/1/2 {
        ipv4-address 10.1.1.1/30;
        ipv6-address 2001:db8::1:1:1/126;
        remote {
            neighbor par-core-2;
            interface 1/1/6;
        }
    }
    backbone-interface par-core-2 1/1/6 {
        ipv4-address 10.1.1.2/30;
        ipv6-address 2001:db8::1:1:2/126;
        remote {
            neighbor par-core-1;
            interface 2/1/2;
        }
    }
}
```
