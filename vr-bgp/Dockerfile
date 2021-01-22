ARG REGISTRY=vrnetlab/
FROM ${REGISTRY}vr-xcon
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    iputils-tracepath \
    procps \
    python3-jinja2 \
    python3-flask \
    python3-pip \
    sqlite3 \
    tcpdump \
    telnet \
    vim \
    wget
RUN pip3 install exabgp


ADD *bgp* /

ENTRYPOINT ["/vr-bgp.py"]
