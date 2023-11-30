# vrnetlab / OpenBSD

This is the vrnetlab docker image for OpenBSD.

This docker image requires a custom-built OpenBSD image with pre-installed [cloud-init](https://cloudinit.readthedocs.io/en/latest/). You can download such images from https://bsd-cloud-image.org/.

## Building the docker image

Run `make download`. It will try to download the latest OpenBSD release from https://bsd-cloud-image.org/ to this directory. Then run `make` to build a docker image.

If for some reasons you can't obtain an image from https://bsd-cloud-image.org/, you can build it yourself with the script from [this repository](https://github.com/goneri/pcib).

It's been tested to boot, respond to SSH and have correct interface mapping
with the following images:

* openbsd-7.3-2023-04-22.qcow2

## Usage

```
docker run -d --privileged --name <container_name> vrnetlab/vr-openbsd:<tag> --username <username> --password <password>
```

Where:

* `container_name` - name of the created container.
* `tag`- OpenBSD release version (e.g., 7.3).
* `username`, `password` - OpenBSD VM credentials.

Example:

```
docker run -d --privileged --name my-obsd-router vrnetlab/vr-openbsd:7.3 --username admin --password admin
```

It will take about 1 minute for the container to boot. After that, you can try to ssh to the container's IP or telnet to port 5000 for console access.

To obtain the container's IP run:

```
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container_name>
```

## Interface mapping

Interface `vio0` is always configured as a management interface. Interfaces `vio1` to `vio17` can be used for data plane.

## System requirements

CPU: 1 core  
RAM: 512MB  
DISK: 4.0GB
