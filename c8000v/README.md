# Cisco Catalyst 8000V Edge Software

This is the vrnetlab docker image for Cisco Catalyst 8000V Edge Software, or
'c8000v' for short.

The Catalyst 8000v platform is a successor to the CSR 1000v. As such, this
platform directory 'c8000v' started off as a copy of the 'csr' directory. With
time we imagine the two platforms will diverge. One such change is already
planned to support using the Catalyst 8000v in one of the two modes:

- regular,
- SD-WAN Controller mode (managed by Viptela).

Right now the SD-WAN flavor is still split off because to enable the Controller
mode you have to effectively boot the router into a completely different mode.
In the near future these modifications will be merged back into the 'c8000v'
platform that will produce both the regular and sd-wan images.

On installation of Catalyst 8000v the user is presented with the choice of
output, which can be over serial console, a video console or through automatic
detection of one or the other. Empirical studies show that the automatic
detection is far from infallible and so we force the use of the serial console
by feeding the VM an .iso image that contains a small bootstrap configuration
that sets the output to serial console. This means we have to boot up the VM
once to feed it this configuration and then restart it for the changes to take
effect. Naturally we want to do this in the build process as to avoid having to
restart the router once for every time we run the docker image. Unfortunately
docker doesn't allow us to run docker build with `--privileged` so there is no
KVM acceleration making this process excruciatingly slow were it to be performed
in the docker build phase. Instead we build a basic image using docker build,
which essentially just assembles the required files, then run it with
`--privileged` to start up the VM and feed it the .iso image. After we are done
we shut down the VM and commit this new state into the final docker image. This
is unorthodox but works and saves us a lot of time.

## Building the docker image

Put the .qcow2 file in this directory and run `make docker-image` and you should
be good to go. The resulting image is called `vr-c8000v`. You can tag it with
something else if you want, like `my-repo.example.com/vr-c8000v` and then push
it to your repo. The tag is the same as the version of the Catalyst 8000v image,
so if you have c8000v-universalk9.16.04.01.qcow2 your final docker image will be
called `vr-c8000v:16.04.01`

It's been tested to boot and respond to SSH with:

- 16.03.01a (c8000v-universalk9.16.03.01a.qcow2)
- 16.04.01 (c8000v-universalk9.16.04.01.qcow2)
- 17.11.01a (c8000v-universalk9_16G_serial.17.11.01a.qcow2)

## Usage

```bash
docker run -d --privileged --name my-c8000v-router vr-c8000v
```

## Interface mapping

IOS XE 16.03.01 and 16.04.01 does only support 10 interfaces, GigabitEthernet1 is always configured
as a management interface and then we can only use 9 interfaces for traffic. If you configure vrnetlab
to use more then 10 the interfaces will be mapped like the table below.

The following images have been verified to NOT exhibit this behavior

- c8000v-universalk9.03.16.02.S.155-3.S2-ext.qcow2
- c8000v-universalk9.03.17.02.S.156-1.S2-std.qcow2

| vr-c8000v | vr-xcon |
| :-------: | :-----: |
|    Gi2    |   10    |
|    Gi3    |    1    |
|    Gi4    |    2    |
|    Gi5    |    3    |
|    Gi6    |    4    |
|    Gi7    |    5    |
|    Gi8    |    6    |
|    Gi9    |    7    |
|   Gi10    |    8    |
|   Gi11    |    9    |

## System requirements

CPU: 1 core

RAM: 4GB

Disk: <500MB

## License handling

You can feed a license file into c8000v by putting a text file containing the
license in this directory next to your .qcow2 image. Name the license file the
same as your .qcow2 file but append ".license", e.g. if you have
"c8000v-universalk9.16.04.01.qcow2" you would name the license file
"c8000v-universalk9.16.04.01.qcow2.license".

The license is bound to a specific UDI and usually expires within a given time.
To make sure that everything works out smoothly we configure the clock to
a specific date during the installation process. This is because the license
only has an expiration date not a start date.

The license unlocks feature and throughput. The default throughput for C8000v is
20Mbit/s which is perfectly for basic management and testing.

## Known issues

If during the image boot process (not during the install process) you notice messages like:

```
% Failed to initialize nvram
% Failed to initialize backup nvram
```

Then the image will boot, but SSH might not work. You still can use telnet to access the running VM. For instance:

```bash
telnet <container name> 5000
```
