FROM ubuntu:xenial
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
    python-dev \
    python-dev \
    python-ipy \
    python-lxml \
    python-pip \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/* \
 && pip install napalm

ADD configengine /

ENTRYPOINT ["/configengine"]
