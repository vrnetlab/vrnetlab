FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
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
   telnet \
   genisoimage \
   dos2unix \
   vim \
   curl \
   && rm -rf /var/lib/apt/lists/*

ARG IMAGE


COPY *.py /
COPY $IMAGE /
EXPOSE 22 161/udp 830 5000 10000-10099 3443 80 443
HEALTHCHECK CMD ["python3", "/healthcheck.py"]
ENTRYPOINT ["/launch.py"]