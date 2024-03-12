ARG REGISTRY=vrnetlab/
FROM ${REGISTRY}vr-xcon
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    iputils-ping \
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
    sudo \
 && rm -rf /var/lib/apt/lists/* \
 && wget -O exabgp.tar.gz https://github.com/Exa-Networks/exabgp/archive/3.4.18.tar.gz \
 && tar zxvf exabgp.tar.gz \
 && cd /exabgp* && python setup.py install \
 && cd / && rm -rf exabgp*

# Allow nobody to sudo without password. The nobody user is used by ExaBGP and we have the
# option to configure a loopback interface for the announced prefixes.
RUN usermod -aG sudo nobody \
 && echo "nobody ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

ADD . /

ENTRYPOINT ["/vr-bgp.py"]
