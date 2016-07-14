FROM debian:stable
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y bridge-utils iproute2 python-ipy qemu-kvm

RUN apt-get install -y python3-ipy

ADD *.vmdk /xrv.vmdk
ADD launch_xrv.py /

ENTRYPOINT ["/launch_xrv.py"]
