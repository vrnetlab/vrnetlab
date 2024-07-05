# SONiC VM

This is the vrnetlab docker image for SONiC's VM.
The scripts in this directory are based on FreeBSD and VSRX kinds.

> Available with [containerlab](https://containerlab.dev) as [`sonic-vm`](https://containerlab.dev/manual/kinds/sonic-vm/) kind.

## Building the docker image

Download the latest `sonic-vs.img.gz` image using the options documented on the [containerlab.dev website](https://containerlab.dev/manual/kinds/sonic-vm/).

Uncompress and place the `.img` file in this directory. Rename the file to `sonic-vs-[version].qcow2` and run `make`.

After typing `make`, a new image will appear named `vrnetlab/vr-sonic:<version>`.

Run `docker images` to confirm this.

## System requirements

- CPU: 2 cores
- RAM: 4GB
- DISK: ~3.2GB

## Configuration

SONiC nodes boot with a basic configuration by default, enabling SSH and basic management connectivity. All factory default configuration is retained.
Full startup configuration can be passed by mounting it under `/config/config_db.json`, this is done automatically by Containerlab. Only SONiC json config format is accepted. This fill will replace existing default config.

## Contact

The author of this code is Adam Kulagowski (<adam.kulagowski@codilime.com>), CodiLime (codilime.com), feel free to reach him in case of problems.
