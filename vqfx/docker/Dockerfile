FROM debian:stretch
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    bridge-utils \
    iproute2 \
    python3 \
    socat \
    qemu-kvm \
 && rm -rf /var/lib/apt/lists/*

ARG RE_IMAGE
ARG PFE_IMAGE

COPY $RE_IMAGE /
COPY $PFE_IMAGE /

RUN echo $RE_IMAGE > /re_image
RUN echo $PFE_IMAGE > /pfe_image

COPY healthcheck.py /
COPY vrnetlab.py /
COPY launch.py /

EXPOSE 22 161/udp 830 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
