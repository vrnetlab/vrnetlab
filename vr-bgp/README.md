vrnetlab BGP speaker
====================
This is vr-bgp, the vrnetlab BGP speaker. It is specifically written as a test
helper for a CI environment so that one can easily test BGP route policies.
Under the hood we use ExaBGP together with a few Python helper programs to
build a dead simple HTTP API.

It uses the vrnetlab xcon program to connect to a virtual router port. See
vr-xcon for more information on how that works under the hood. Naturally it
assumes the router to test is a vrnetlab router of some sort.

The idea is that you CI runner spins up one or more virtual routers of your
choice, starts one or more vr-bgp instances to simulate different BGP
relations, then instructs the vr-bgp instances to announce routes and checks
the received routes to verify they comply with the routing policy.

For example, a service provider network typically has different classes of BGP
neighbors, e.g.:

 * iBGP full-mesh between core routes
 * iBGP route reflector sessions from core to edge routers
 * eBGP to peering partners
 * eBGP to customers
 * ...

One would setup a vr-bgp instance to simulate each of these classes. Tell the
"peering partner class vr-bgp" instance to announce 1.2.3.0/24 and you can then
look at the vr-bgp instance simulating the iBGP full-mesh to make sure you
properly receive this prefix, that it has the correct communities,
local-preference and that MED is stripped / zeroized (if that is what you
want!). Since the testing happens over a standard interface (BGP) it is simple
to replace the virtual router with another vendor's and thus verify that the
routing policy of all your vendors ultimately do the same thing.

Configuring the virtual router is outside the scope of vrnetlab - you are
supposed to use your normal provisioning system for this.

vr-bgp exposes a super simple HTTP API to announce routes and collect received
routes.

vr-bgp only supports a single BGP neighbor (well, one per AFI - IPv4 / IPv6) at
a time which might seem tedious at first but it also simplifies things a lot as
we don't have to key information on individual neighbors.

next-hops are stored as attributes of a prefix, which isn't entirely correct as
it's really part of the NLRI information in BGP updates and not part of the
path attributes. However, putting it as an attribute vastly simplifies things.
The primary drawback is that there is no way to tell two prefixes with
different next-hops apart. This normally does not happen for vr-bgp since we
only have one BGP neighbor per AFI and that neighbor will only announce one
next-hop per prefix but this might make us incompatible with BGP add-path.

API
---
The vr-bgp API is a very simple RESTful API running by default on port 5000, exposing three endpoints:
 * `GET http://docker-ip:5000/neighbors`: lists all configured neighbors and connection states
 * `GET http://docker-ip:5000/received`: lists all received prefixes by address family and their attributes
 * `POST http://docker-ip:5000/announce`: announces the prefixes specified in the body of the request, with optional attributes

### `GET /neighbors`
```javascript
{
    "192.168.21.2": {
        "state": "up",
        "timestamp": "2017-05-31 07:42:06"
    },
    "2001:db8:5::21:2": {
        "state": "up",
        "timestamp": "2017-05-31 07:42:06"
    }
}
```

The example shows a vr-bgp speaker configured with two neighbors. Connections
to both neighbors are established.

### `GET /received`
```javascript
{
    "ipv4 unicast": {
        "22.0.0.0/24": {
            "as-path": [
                2792,
                22
            ],
            "community": [
                [
                    2792,
                    10300
                ],
                [
                    2792,
                    11276
                ]
            ],
            "confederation-path": [],
            "next-hop": "192.168.22.1",
            "origin": "igp"
        }
    },
    "ipv6 unicast": {
        "2001:11::/64": {
            "as-path": [
                2792,
                11
            ],
            "community": [
                [
                    11,
                    1234
                ]
            ],
            "confederation-path": [],
            "next-hop": "2001:db8:5::22:1",
            "origin": "igp"
        }
    }
}
```

The example shows two received prefixes for IPv4 and IPv4 address family with
all attributes. Note that community string `2792:10300` is broken down into a
list of integers `[2792, 10300]`.

### `POST /announce`
```javascript
{"routes":
    [
        { "prefix": "21.0.0.0/24" },
        { "prefix": "21.1.0.0/24", "community": ["2792:10300"]},
        { "prefix": "21.2.0.0/24", "as-path": [21, 65000] },
        { "prefix": "21.3.0.0/24", "med": 100 }
    ]
}
```

The example shows announcement configuration for four prefixes. By default, all
prefixes originate in the local AS (21 in this example).

Additional attributes exposed through the API are:
 * `community`: set any number of communities by providing a list of strings
   `["x:y", "w:z"]`
 * `as-path`: override the default as-path (local-as) by providing a list of
   integers `[21, 65000]`
 * `med`: set multi-exit discriminator (MED) attribute to an integer value

Example
-------
See the example directory for a full blown example of vr-bgp in action to
verify a network's BGP routing policy.
