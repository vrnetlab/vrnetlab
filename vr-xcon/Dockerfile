FROM debian:bullseye AS build
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    gnupg \
    wget \
 && wget -q -O - https://apt.acton-lang.io/acton.gpg | apt-key add - \
 && echo "deb [arch=amd64] http://apt.acton-lang.io/ bullseye main" >> /etc/apt/sources.list.d/acton.list \
 && apt-get update \
 && apt-get install -qy acton \
 && rm -rf /var/lib/apt/lists/*

COPY xcon.act /xcon.act
RUN actonc /xcon.act

FROM debian:bullseye
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
    python3-pip \
 && pip3 install scapy \
 && rm -rf /var/lib/apt/lists/*

ADD xcon.py /

COPY --from=build /xcon /xcon

# The first line in the health file is the exit code: 0 or 1. The following lines are the output message
HEALTHCHECK --interval=5s --start-period=1s CMD sed 1d /health; exit `head -n1 /health`
ENTRYPOINT ["/xcon.py"]
