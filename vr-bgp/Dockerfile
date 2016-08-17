FROM vrnetlab/vr-xcon
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    git \
    golang \
    python \
    python-setuptools \
    python3-jinja2 \
    python3-flask \
    wget \
 && rm -rf /var/lib/apt/lists/*

RUN wget -O exabgp.tar.gz https://github.com/Exa-Networks/exabgp/archive/3.4.16.tar.gz \
 && tar zxvf exabgp.tar.gz \
 && cd /exabgp* && python setup.py install

ADD vr-bgp.py /
ADD exabgp.conf.tpl /
ADD bgpapi.py /
ADD bgprec.py /

ENTRYPOINT ["/vr-bgp.py"]
