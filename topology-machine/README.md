vrnetlab topology machine
=========================
The topology machine will help you manage a topology of virtual routers.

In particular, there are two activites related to building a topology that can
be really tedious and topology machine is meant to help you with these:

 * building a full-mesh
 * assigning interfaces to 

Full-meshes defined in the configuration file will be expanded into
point-to-point links between all the member routers.

Each point-to-point link needs to have an interface assigned on the routers on
the respective ends of the link. Once you have more than a handful of links it
can become really tedious to sort out what goes where and any additions or
deletions to your topology means instant headache... which is where topo
machine comes in.

To convert a topology configuration into a ready to run topology use --build:
```
topo --build my-topology-config.json > my-topo.json
```
The output is printed to stdout so you can view it, pipe or redirect to a file
if you want.

topology machine is also able to run the machines for you, i.e. execute docker
run for the routers defined in the configuration file and start tcpbridge with
the relevant arguments to complete the topology:
```
topo --run my-topo.json
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
align with the "physical" topology built by tcpbridge it makes sense to let
topology machine assist you in producing this service config.

Use `--template` to produce output based on the provided topology information
and template:
```
topo --template my-topo.json my-template.template
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
