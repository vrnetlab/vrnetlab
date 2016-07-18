FROM debian:stable
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    bridge-utils \
    iproute2 \
    python3-ipy \
    socat \
    qemu-kvm \
 && rm -rf /var/lib/apt/lists/*

ADD *.qcow2 /sros.qcow2
ADD launch_vsr.py /

EXPOSE 22 830 5000
EXPOSE 10000-10099
ENTRYPOINT ["/launch_vsr.py"]
