FROM debian:stretch
MAINTAINER Kristian Larsson <kristian@spritelink.net>

RUN apt-get update -qy \
    && apt-get upgrade -qy \
    && apt-get install -y \
        qemu-kvm \
        bridge-utils \
        socat \
        iproute2 \
        python3-ipy \
        python3-pexpect \
        ssh \
    && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE /
COPY *.py /
EXPOSE 22 830 5000 10000-10099

HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
