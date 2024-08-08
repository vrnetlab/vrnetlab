FROM public.ecr.aws/docker/library/debian:bookworm-slim
LABEL maintainer="Kristian Larsson <kristian@spritelink.net>"
LABEL maintainer="Roman Dodin <dodin.roman@gmail.com>"
LABEL maintainer="Stefano Sasso <stesasso@gmail.com>"

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qy \
 && apt-get install --no-install-recommends -y \
    dosfstools \
    bridge-utils \
    iproute2 \
    python3 \
    socat \
    ssh \
    tcpdump \
    qemu-kvm \
    qemu-utils \
    inetutils-ping \
    dnsutils \
    telnet \
 && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE* /
COPY *.py /

EXPOSE 22 80 161/udp 443 830 5000 6030 10000-10099 57400
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
