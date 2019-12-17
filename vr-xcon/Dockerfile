FROM debian:stretch
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    bridge-utils \
    iproute2 \
    python3-ipy \
    tcpdump \
    telnet \
 && rm -rf /var/lib/apt/lists/*

ADD xcon.py /

ENTRYPOINT ["/xcon.py"]
