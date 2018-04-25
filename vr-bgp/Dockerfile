ARG REGISTRY=vrnetlab/
FROM ${REGISTRY}vr-xcon
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    iputils-tracepath \
    git \
    golang \
    procps \
    python \
    python-setuptools \
    python3-jinja2 \
    python3-flask \
    tcpdump \
    telnet \
    wget \
 && rm -rf /var/lib/apt/lists/* \
 && wget -O exabgp.tar.gz https://github.com/Exa-Networks/exabgp/archive/3.4.18.tar.gz \
 && tar zxvf exabgp.tar.gz \
 && cd /exabgp* && python setup.py install \
 && cd / && rm -rf exabgp*

ADD . /

ENTRYPOINT ["/vr-bgp.py"]
