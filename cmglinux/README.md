# CMG Linux VM

## Introduction

CMG Linux is utilized as a DB VM as one of Nokia MAG-C VMs.
The image of CMG Linux is released in qcow2 format.
Since some of MAG-C tools in CMG Linux are written with systemd or systemctl utilization,
then CMG Linux cannot be containerized because docker does not run systemd inside the container.
Given this reasoning, the approach to containerized CMG Linux is to create a container
to run a CMG Linux VM in the same way Vrnetlab has done.

## Build the docker image

It is required to provide CMG Linux qcow2 image to build the docker image.
Nokia representative can provide the qcow2 file.

Make sure that your python virtualenv has `yaml` package installed.

Copy the `cmg-linux.qcow2` file in `vrnetlab/cmglinux` directory
and rename the file by appending the version to it.
For example, for CMG Linux version 24.3.r1,
make sure that the qcow2 file will be named as `cmg-linux-24.3.R1.qcow2`.
The version 24.3.R1 will be used as a container image tag.

Run `make docker-image` to start the build process.
The resulting image is called `vrnetlab/cmglinux:<version>`.
You can tag it with something else. for example, `cmglinux:<version>`.

## Host requirements

* 4 vCPU
* 6 GB RAM

## Configuration

Initial config is carried out via cloud-init.
By default CMG-Linux boots by using a pre-defined cloud-init config drive.

Custom configuration can be added by binding the local `config_drive`
directory to `/config_drive` directory in the container.
The accepted structure of `config_drive`is shown below.
Any other directories or files not specified below are ignored.

``` text
config_drive/
└── openstack/
    ├── latest/
    │   ├── meta_data.json
    │   └── user_data
    └── content/
        ├── 0000 (referenced content files)
        ├── 0001
        └── ....
```

The internal `launch.py` script also modifies the content of `user_data` to add `clab`as
default user with password `clab@123`. Moreover, it also modifies `user_data`
to configure the management network interface.

Also `9.9.9.9` configured as the DNS resolver. Change it with `resolvectl` if required.

## Example containerlab topology

Below is an example of Containerlab topology using CMG Linux.

``` yaml
name: test_cmglinux
prefix: __lab-name
topology:
  nodes:
    cmg-1:
      kind: generic_vm
      image: vrnetlab/vr-cmglinux:24.3.R3
      binds:
        - config_drive_cmg1:/config_drive
    cmg-2:
      kind: generic_vm
      image: vrnetlab/vr-cmglinux:24.3.R1
      binds:
        - config_drive_cmg2:/config_drive
    alpine:
      kind: linux
      image: alpine:dev
  links:
  - endpoints:
      - cmg-1:eth1
      - alpine:eth1
  - endpoints:
      - cmg-1:eth2
      - alpine:eth2
  - endpoints:
      - cmg-1:eth3
      - alpine:eth3
  - endpoints:
      - cmg-2:eth1
      - alpine:eth4
  - endpoints:
      - cmg-2:eth2
      - alpine:eth5
```
