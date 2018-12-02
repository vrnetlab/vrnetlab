vrnetlab / Nokia VSR SROS
=========================
This is the vrnetlab docker image for Nokia VSR / SROS.

Ask your Nokia representative for the VSR image.  Put the sros.qcow2 file in
this directory and run `make docker-image` and you should be good to go. The
resulting image is called `vr-sros`. You can tag it with something else if you
want, like `my-repo.example.com/vr-sros` and then push it to your repo.

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to at least boot with:

 * 12.0.R6
 * 13.0.R7
 * 14.0.R4
 * 14.0.R5
 * 16.0.R1
 * 16.0.R2
 * 16.0.R2-1
 * 16.0.R3
 * 16.0.R3-1
 * 16.0.R4
 * 16.0.R4-1

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-sros-router vr-sros
```
It takes about 90 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

You can specify how many ports the virtual router should have through the
`--num-nics` argument. With 5 or fewer ports the router will be started in what
is called "integrated" mode which means it's a single VM. The router will then
be equipped with a m5-1gb-sfp-b MDA. The VSR release notes claim that up to 8
interfaces can be used but I have never gotten more than 5 to work (even when
using a different MDA).

If more than 5 ports are specified with the `--num-nics` argument the router
will be started in what is known as "distributed" mode which means multiple VMs
are used. The first VM is the control plane while remaining are "line cards".
Again, the release notes state that 8 ports can be used per VM but I have not
been able to get link up on more than 6 interface per line card VM. Thus, the
number of line card VM started is dependent upon the number of ports specified
through `--num-nics`. `--num-nics 6` means one line card VM (and one control
plane VM) is started whereas `--num-nics 15` would yield three line card VMs
(3x6=18 ports). In distributed mode the router is simulating an XRS-20. Each
line card is equipped with one cx20-10g-sfp MDA (XMA really). Note how each VM,
both control plane and line card, consume 6GB of RAM each.

The ports follow the pattern X/1/[1..6] where X is the line card slot. For an
integrated VM the slot is always 1 whereas for distributed mode there can be
many line card slots.

If you want to look at the startup process you can specify `-i -t` to docker
run and you'll get an interactive terminal, do note that docker will terminate
as soon as you close it though. Use `-d` for long running routers.


License handling
----------------
You can feed a license file into SROS by putting a text file containing the
license in this directory next to your .qcow2 image.  Name the license file the
same as your .qcow2 file but append ".license", e.g. if you have
"sros-14.0.R3.qcow2" you would name the license file
"sros-14.0.R3.qcow2.license".

The license is bound to a specific UUID and usually expires within a given
time. The UUID is the first part of the license file and the launch script will
automatically extract this and start the VSR with this UUID.

If you have a time limited license you can put the start time of the license in
the license file simply by appending the date in ISO-8601 format (YYYY-mm-dd).
The license usually has a '# BLA BLA TiMOS-XX.Y.*' at the end to signify what
it is for, simply append the date there. The launch script will extract this
date and start the VSR with this date + 1 day as to fool the licensing system.
I suppose that you shouldn't configure NTP or similar on your VSR....


FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: I can't run any useful commands, like "configure", what up?
A: Are you perhaps using release 14? Nokia introduced more limitations on the
VSR when run without license. Apparently it wasn't enough to restart once an
hour and have severe rate-limiting (250pps per interface) but they also limited
the commands you can run, including "configure", which makes the VSR with SROS
14 and later completely useless without a license.

##### Q: How many interfaces are available?
A: Many! You can specify the number of ports you want with the `--num-nics`
argument. If you specify more than 5 the router will be started in
"distributed" mode which means multiple line cards (VMs) are used.

##### Q: Why 6GB of RAM? It says only 4GB is required.
A: SROS 16 seems to require 6GB and we don't build with different amount of
CPU/RAM per versions so that's why every version gets the same.
