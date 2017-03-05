FROM debian:testing
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

#RUN echo "deb http://se.archive.ubuntu.com/ubuntu/ xenial multiverse" >> /etc/apt/sources.list
#RUN echo "deb http://se.archive.ubuntu.com/ubuntu/ xenial-updates multiverse" >> /etc/apt/sources.list

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    bridge-utils \
    iproute2 \
    ovmf \
    python3-ipy \
    socat \
    qemu-kvm \
    wget \
 && rm -rf /var/lib/apt/lists/*

RUN wget -O /bios.bin https://github.com/travisg/uefi/raw/master/ovmf/OVMF.fd

ARG IMAGE
COPY $IMAGE* /
COPY *.py /

EXPOSE 22 830 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
