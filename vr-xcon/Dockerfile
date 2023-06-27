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
 && rm -rf /var/lib/apt/lists/*

ADD xcon.py /

COPY --from=build /xcon /xcon

ENTRYPOINT ["/xcon.py"]
