FROM ubuntu:20.04
MAINTAINER Kristian Larsson <kristian@spritelink.net>
MAINTAINER Roman Dodin <dodin.roman@gmail.com>

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    bridge-utils \
    iproute2 \
    python3-ipy \
    socat \
    qemu-kvm \
    tcpdump \
    ssh \
    inetutils-ping \
    dnsutils \
    telnet \
 && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE* /
COPY *.py /

EXPOSE 22 161/udp 830 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
