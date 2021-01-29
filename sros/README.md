# vrnetlab / Nokia VSR SROS

This is the vrnetlab docker image for Nokia VSR / SROS.

> Originally developed by Kristian Larsson (@plajjan), forked by @hellt to be adapted to work with docker-based networking dataplane.  
> Refer to ["Added in this fork"](#added-in-this-fork) section to read on the differences between this fork and the upstream version.

## Building the docker image
Ask your Nokia representative for the VSR/VSIM image.
Copy the `sros-vm.qcow2` file in `vrnetlab/sros` directory and rename the file by appending the SR OS version to it.  
For example, for SR OS version 20.10.r1 make sure that the qcow2 file will be named as `sros-vm-20.10.R1.qcow2`. The version (20.10.R1) will be used as a container image tag.

Apart from the qcow file itself, the license 

Run `make docker-image` to start the build process. The resulting image is called `vrnetlab/vr-sros:<version>`. You can tag it with something else if needed, like `vr-sros:<version>`.

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to run with the following versions:

 * 20.10.R1

## Variants
Nokia SR OS virtualized simulator (VSIM) can be configured to emulate many chassis and cards combinations.

To give vrnetlab users flexibility of choice, this fork provides a number of such combinations, which are called _variants_.

By selecting a certain variant (referred by its `name`) the VSIM will start with the certain configuration as per the following table:

|    Name     |    mode     |     Control plane      |         Line card         | RAM (GB) | Max NICs |
| :---------: | :---------: | :--------------------: | :-----------------------: | :------: | :------: |
|    sr-1     | integrated  |         cpm-1          |     me12-100gb-qsfp28     |    5     |    12    |
|    sr-1e    | distributed |         cpm-e          |       me40-1gb-csfp       |   4+4    |    40    |
|    sr-1s    | integrated  |         xcm-1s         |     s36-100gb-qsfp28      |    5     |    36    |
|    sr-1s    | integrated  |         xcm-1s         |     s36-100gb-qsfp28      |    5     |    36    |
|   sr-14s    | distributed |     sfm-s+xcm-14s      |     s36-100gb-qsfp28      |   4+6    |    36    |
| ixr-e-small | distributed | imm14-10g-sfp++4-1g-tx |   m14-10g-sfp++4-1g-tx    |   3+4    |    18    |
|  ixr-e-big  | distributed |       cpm-ixr-e        | m24-sfp++8-sfp28+2-qsfp28 |   3+4    |    34    |
|   ixr-r6    | integrated  |      cpiom-ixr-r6      |  m6-10g-sfp++4-25g-sfp28  |    6     |    10    |
|    ixr-s    | integrated  |       cpm-ixr-s        |     m48-sfp++6-qsfp28     |   3+4    |    54    |

The variants are [defined in the code](https://github.com/hellt/vrnetlab/blob/bf70a9a9f2f060a68797a7ec29ce6aea96acb779/sros/docker/launch.py#L38-L66) as a dictionary. If a new variant is needed, feel free to adjust the data structure and build an image.

## Usage (not updated yet)

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


## License handling

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

# Added in this fork
This fork packs a lot of changes related to SR OS.
Fist it uses a notion of variants, which is a code name of a SR OS emulated hardware. See [variants](#variants).

Next it exposes the management interface of the SR OS VM as an interface connected to the bridge `br-mgmt` and runs its own tftpd server so that SR OS VMs can write their config to this tftpd location.