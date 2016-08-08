vrnetlab / Nokia VSR SROS
=========================
This is the vrnetlab docker image for Nokia VSR / SROS.

Ask your Nokia representative for the VSR image.  Put the sros.qcow2 file in
this directory and run `make docker-image` and you should be good to go. The
resulting image is called `vr-sros`. You can tag it with something else if you
want, like `my-repo.example.com/vr-sros` and then push it to your repo.

This is currently using the "integrated" VSR mode which is single-VM approach.
It works great for testing control plane type of things but the forwarding
plane is lacking a lot of features, most notably CPM filters which means you
can't protect the control plane through policers and whatnot.

Yes, we probably should try to switch to a distributed VSR mode.

It's been tested to at least boot with:

 * 12.0.R6

Usage
-----
The container must be `--privileged` to start KVM.
```
docker run -d --privileged --name my-sros-router vr-sros
```
It takes about 90 seconds for the virtual router to start and after this we can
login over SSH / NETCONF with the specified credentials.

The router is "equipped" with three m20-1gb-xp-sfp MDAs which yields a total of
60 ports although we typically can't expose more than ~30 due to PCI bus
limits. The launch script defaults to 20 NICs. I haven't tested to go beyond
that. The ports are numbered 1/1/[1-20], 1/3/[1-20] and 1/5/[1-20].

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
the license file, simply by appending the date in ISO-8601 format (YYYY-mm-dd).
The license usually has a '# BLA BLA TiMOS-XX.Y.*' at the end to signify what
it is for, simply append the date there. The launch script will extract this
date and start the VSR with this date + 1 day as to fool the licensing system.
I suppose that you shouldn't configure NTP or similar on your VSR....

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: I can't run any useful commands, like "configure", what up?
A: Are you perhaps using release 14? Nokia introduced more limitations on the
VSR when run without license. Apparently it wasn't enough to restart once an
hour and have severe rate-limiting (200pps per interface) but they also limited
the commands you can run, including "configure", which makes the VSR completely
useless without a license.

##### Q: How many interfaces are available?
A: Without a license; 12.0 seems to support up to 14 interfaces. 13.0 does 5.
Not sure about 14.
