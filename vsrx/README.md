# Juniper vSRX

This is the vrnetlab docker image for Juniper's vSRX.
Both "classic" vSRX 2.0 and the new vSRX 3.0 images are compatible with this vrnetlab kind.

> Available with [containerlab](https://containerlab.dev) as `juniper_vsrx` kind.

## Building the docker image

Download the vSRX 3.0 trial `.qcow2` image from https://support.juniper.net/support/downloads/?p=vsrx-evaluation
and place it in this directory. A Juniper account is required to download the evaluation image.

After typing `make`, a new image will appear called `vrnetlab/vjunosevolved`.
Run `docker images` to confirm this.

## System requirements

CPU: 2 cores
RAM: 4GB
DISK: Depends on kind. vSRX 2.0: ~4-5GB; vSRX 3.0: ~1.5GB

## Configuration

vSRX nodes boot with a basic configuration by default, enabling SSH and Netconf, and basic management connectivity. All factory default configuration is removed.
Further startup configuration can be passed by mounting it under `/config/startup-config.cfg`, this is done automatically by Containerlab. Only Juniper conf format is accepted.

Note: The last version of vrnetlab to support `set` command-based startup configurations in vSRX is v0.17.1. A tool like [junoser](https://github.com/codeout/junoser) might help with converting your startup configurations to the canonical Juniper conf format.
