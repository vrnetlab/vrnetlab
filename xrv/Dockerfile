FROM debian:stable
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    bridge-utils \
    iproute2 \
    python3-ipy \
    qemu-kvm \
 && rm -rf /var/lib/apt/lists/*

ADD *.vmdk* /xrv.vmdk
ADD launch_xrv.py /

EXPOSE 5000
EXPOSE 10000-10099
ENTRYPOINT ["/launch_xrv.py"]
