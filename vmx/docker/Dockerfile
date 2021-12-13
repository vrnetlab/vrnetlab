FROM debian:stretch
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

COPY vmx /vmx
COPY *.py /
COPY juniper.conf /

EXPOSE 22 161/udp 830 5000 10000-10099
# mgmt and console ports for re1
EXPOSE 1022 1161/udp 1830 5001
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
