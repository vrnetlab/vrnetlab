FROM debian:stable
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y bridge-utils iproute2 python-ipy qemu-kvm

RUN apt-get install -y python3-ipy

ADD *.qcow2 /sros.qcow2
ADD launch_vsr.py /

ENTRYPOINT ["/launch_vsr.py"]
