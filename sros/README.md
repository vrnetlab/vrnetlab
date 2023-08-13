# vrnetlab / Nokia VSR SROS

This is the vrnetlab docker image for Nokia VSR / SROS.

## Building the docker image

Ask your Nokia representative for the VSR/VSIM image.
Copy the `sros-vm.qcow2` file in `vrnetlab/sros` directory and rename the file by appending the SR OS version to it.  
For example, for SR OS version 20.10.r1 make sure that the qcow2 file will be named as `sros-vm-20.10.R1.qcow2`. The version (20.10.R1) will be used as a container image tag.

Run `make docker-image` to start the build process. The resulting image is called `vrnetlab/vr-sros:<version>`. You can tag it with something else if needed, like `vr-sros:<version>`.

It's been tested to run with the following versions:

* 20.10.R1 --  20.10.R3
* 21.2.R1

## Variants

Nokia SR OS virtualized simulator (VSIM) can be configured to emulate many chassis and cards combinations.

To give vrnetlab users the flexibility of choice, this fork provides a number of such combinations, which are called _variants_.

By selecting a certain variant (referred by its `name`) the VSIM will start with a certain configuration as per the following table:

|     Name     |    mode     |     Control plane      |            Line card             | RAM (GB) | Max NICs |
| :----------: | :---------: | :--------------------: | :------------------------------: | :------: | :------: |
|     sr-1     | integrated  |         cpm-1          |        me12-100gb-qsfp28         |    5     |    12    |
|    sr-1e     | distributed |         cpm-e          |          me40-1gb-csfp           |   4+4    |    40    |
|  sr-1e-sec   | distributed |         cpm-e          | me12-10/1gb-sfp+ and isa2-tunnel |   4+4    |    12    |
|    sr-1s     | integrated  |         xcm-1s         |         s36-100gb-qsfp28         |    6     |    36    |
| sr-1s-macsec | integrated  |         xcm-1s         | ms16-100gb-sfpdd+4-100gb-qsfp28  |    6     |    20    |
|    sr-2s     | distributed |         cpm-2s         |  ms8-100gb-sfpdd+2-100gb-qsfp28  |   3+4    |    10    |
|    sr-7s     | distributed |     sfm2-s+xcm2-7s     |     x2-s36-800g-qsfpdd-18.0t     |   4+6    |    36    |
|  sr-7s-fp4   | distributed |      sfm-s+xcm-7s      |         s36-100gb-qsfp28         |   4+6    |    36    |
|    sr-14s    | distributed |     sfm-s+xcm-14s      |         s36-100gb-qsfp28         |   4+6    |    36    |
|    sr-a4     | distributed |         cpm-a          |     maxp10-10/1gb-msec-sfp+      |   4+4    |    10    |
| ixr-e-small  | distributed | imm14-10g-sfp++4-1g-tx |       m14-10g-sfp++4-1g-tx       |   3+4    |    18    |
|  ixr-e-big   | distributed |       cpm-ixr-e        |    m24-sfp++8-sfp28+2-qsfp28     |   3+4    |    34    |
|    ixr-ec    | integrated  |       cpm-ixr-e        |  m4-1g-tx+20-1g-sfp+6-10g-sfp+   |    4     |    34    |
|    ixr-r6    | integrated  |      cpiom-ixr-r6      |    m6-10g-sfp++1-100g-qsfp28     |    6     |    10    |
|    ixr-s     | integrated  |       cpm-ixr-s        |        m48-sfp++6-qsfp28         |   3+4    |    54    |

The variants are [defined in the code](https://github.com/hellt/vrnetlab/blob/bf70a9a9f2f060a68797a7ec29ce6aea96acb779/sros/docker/launch.py#L58) as a dictionary. If a variant you need is not in the table, use the `custom` variant and define the emulated platform yourself as described below.

### Custom variant

It is possible to provide a custom variant. For that, the variant argument must be formed in one of the following way, depending on the integrated or distributed platform:

**Integrated**

```bash
cpu=2 ram=4 max_nics=6 chassis=sr-1 slot=A card=cpm-1 slot=1 mda/1=me6-100gb-qsfp28
```

**Distributed**

```bash
# for distributed chassis CPM and IOM are indicated with markers cp: and lc:
# notice the delimiter string `___` that MUST be present between CPM and IOM portions
# max_nics value is provided in lc part.
# mem is provided in GB
cp: cpu=2 ram=4 chassis=ixr-e slot=A card=cpm-ixr-e ___ lc: cpu=2 ram=4 max_nics=34 chassis=ixr-e slot=1 card=imm24-sfp++8-sfp28+2-qsfp28 mda/1=m24-sfp++8-sfp28+2-qsfp28
```

Custom variants WILL NOT have cards/mda auto-configured, user needs to configure those manually once the node finishes boot process.

## Usage with containerlab

Refer to containerlab documentation piece on [vrnetlab integration](https://containerlab.srlinux.dev/manual/vrnetlab/) and vr-sros.

## Extracting qcow2 from container image

It is possible to extract the original qcow2 disk image from an existing container image. This might be useful when you want to rebuild the container image with a different vrnetlab codebase.

The following script takes an image name and the qcow2 image name to copy out from the container image:

```bash
IMAGE=registry.srlinux.dev/pub/vr-sros:23.7.R1
VERSION=$(cut -d ':' -f 2 <<< $IMAGE)
docker create --name sros-copy $IMAGE
docker cp sros-copy:sros-vm-$VERSION.qcow2 .
docker rm sros-copy
```
