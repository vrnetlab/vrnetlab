# Cisco IOL (IOS on Linux)

This is the containerlab/vrnetlab image Cisco IOL.

CML recently introduced IOL-XE which compared to other Cisco images, runs very lightly since it executes purely as a binary and has no requirement for a virtualisation layer.

There are two types of IOL you can obtain:

- IOL, meant for Layer 3 operation as a router.
- IOL-L2, meant to act as a L2/L2+ switch.

## Building the image

> This README is for the IOL image, if you are trying to build the IOL-L2 image, go to the `../iol-l2` directory.

Copy the `x86_64_crb_linux-adventerprisek9-ms` and rename it to `cisco_iol-x.y.z.bin` (x.y.z being the version number). For example `cisco_iol-17.12.01.bin`. The `.bin` extension is important.

> If you are getting the image from the CML refplat, the IOL image is under the `iol-xe-x.y.z` directory.

### License (.iourc)

Unlike the older IOU (IOS on Unix) a `.iourc` license file may not be required, however you still can provide one if necessary.

The `.iourc` license file can be placed next to the IOL binary (in this directory).

When supplying a `.iourc` license file, the hostname field must be changed to `iol`

**BEFORE**

```ini
[license]
hostname = a1b2c3d4e5f6g7
```

**AFTER**

```ini
[license]
iol = a1b2c3d4e5f6g7
```

### Build command

Execute

```
make docker-image
```

and the image will be built and tagged. You can view the image by executing `docker images`.

```
containerlab@containerlab:~$ docker images
REPOSITORY                      TAG         IMAGE ID       CREATED          SIZE
vrnetlab/vr-iol                 17.12.01    44dde64d56ad   21 hours ago     741MB
```

## Usage

You can define the image easily and use it in a topology.

```yaml
# topology.clab.yaml
name: mylab
topology:
  nodes:
    iol:
      kind: cisco_iol
      image: vrnetlab/vr-iol:<tag>
```
