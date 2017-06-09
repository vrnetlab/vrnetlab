FROM debian:stable
MAINTAINER Fredrik Holmberg <fredrik@equanic.com>

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

ARG IMAGE
COPY $IMAGE* /
COPY *.py /
COPY qemu-commands.txt

EXPOSE 22 830 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
