vrnetlab BGP speaker
====================
This is vrp-bgp, the vrnetlab BGP speaker. It is specifically written as a test
helper for a CI environment so that one can easily test BGP route policies.

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

Configuring the virtual router it outside the scope of vrnetlab - you are
supposed to use your normal provisioning system for this.

vr-bgp exposes a super simple HTTP API to announce routes and collect received
routes.

vr-bgp only supports a single BGP neighbor at a time which might seem tedious
at first but it also simplifies things a lot as we can key information merely
on bgp speaker rather than on individual neighbors.
