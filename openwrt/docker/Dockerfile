FROM alpine:3.18
MAINTAINER Andreas Cymbal takalele@konnex.me

RUN apk add --no-cache bash \
    qemu-system-x86_64 \
    qemu-img \
    socat \
    net-tools \
    iproute2 \
    bridge-utils \
    python3 \
    py3-click \
    nano \
    vim \
    py3-pip && ln -sf python3 /usr/bin/python

RUN pip3 install --no-cache --upgrade pip setuptools
RUN pip install IPy

ARG IMAGE
COPY $IMAGE* /
COPY *.py /

EXPOSE 22 161/udp 80 830 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]