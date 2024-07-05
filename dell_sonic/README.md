# Dell Enterprise SONiC

This is the vrnetlab docker image for SONiC's VM.
The scripts in this directory are based on FreeBSD and VSRX kinds.

> Available with [containerlab](https://containerlab.dev) as [`dell_sonic`](https://containerlab.dev/manual/kinds/dell_sonic/) kind.

## Building the docker image

Download the latest Dell SONiC qcow2 disk image from Dell support website. Rename the file to `dell-sonic-[version].qcow2` and run `make`.

After typing `make`, a new image will appear named `vrnetlab/vr-dell_sonic:<version>`. Run `docker images` to confirm this.

## System requirements

- CPU: 2 cores
- RAM: 4GB
- DISK: ~3.2GB

## Configuration

SONiC nodes boot with a basic configuration by default, enabling SSH and basic management connectivity. All factory default configuration is retained.
Full startup configuration can be passed by mounting it under `/config/config_db.json`, this is done automatically by Containerlab. Only SONiC json config format is accepted. This fill will replace existing default config.
