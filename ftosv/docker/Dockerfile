FROM ubuntu:20.04
LABEL maintainer="Kristian Larsson <kristian@spritelink.net>"
LABEL maintainer="Roman Dodin <dodin.roman@gmail.com>"

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qy \
   && apt-get upgrade -qy \
   && apt-get install -y \
   bridge-utils \
   iproute2 \
   python3-ipy \
   socat \
   qemu-kvm \
   tcpdump \
   tftpd-hpa \
   ssh \
   inetutils-ping \
   dnsutils \
   openvswitch-switch \
   iptables \
   nftables \
   telnet \
   && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE* /
COPY *.py /

EXPOSE 22 80 161/udp 443 830 5000 6030 10000-10099 57400
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
