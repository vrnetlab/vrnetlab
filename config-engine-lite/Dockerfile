FROM ubuntu:jammy
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    bridge-utils \
    iproute2 \
    libffi-dev \
    libffi-dev \
    libjpeg8-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libyaml-dev \
    python3-dev \
    python3-ipy \
    python3-lxml \
    python3-pip \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install napalm

ADD configengine /

ENTRYPOINT ["/configengine"]
