FROM public.ecr.aws/docker/library/debian:bookworm-slim
LABEL org.opencontainers.image.authors="roman@dodin.dev,vista@birb.network"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get install --no-install-recommends -y \
    dosfstools \
    bridge-utils \
    iproute2 \
    python3 \
    socat \
    ssh \
    qemu-kvm \
    qemu-utils \
    inetutils-ping \
    dnsutils \
    telnet \
 && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE* /

# copy conf file
COPY init.conf /
# copy config shell script
COPY make-config.sh /
# copy python scripts for launching VM
COPY *.py /

EXPOSE 22 161/udp 830 5000 10000-10099 57400
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
