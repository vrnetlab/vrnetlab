vrnetlab - VR Network Lab
-------------------------

vrnetlab is built to help you start virtual routers in a convenient way.

It's been developed by Kristian Larsson at Deutsche Telekom as part of the
automated CI test system for the TeraStream project.

FAQ
---
Q: Why don't you ship pre-built docker images?
A: I don't think I'm allowed to ship virtual router images so you just have to
   build the docker images yourself.

Q: Why don't you ship docker images where I can provide the image through a volume?
A: I don't like the concept as it means you have to ship around an extra file.
   If it's a self-contained image then all you have to do is push it to your
   docker registry and then ask a box in your swarm cluster to spin it up!
