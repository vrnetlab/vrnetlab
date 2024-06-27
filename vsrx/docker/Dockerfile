FROM public.ecr.aws/docker/library/debian:bookworm-slim
LABEL org.opencontainers.image.authors="roman@dodin.dev,vista@birb.network"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
   && apt-get install --no-install-recommends -y \
   bridge-utils \
   iproute2 \
   python3 \
   socat \
   qemu-kvm \
   qemu-utils \
   genisoimage \
   && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE* /

COPY init.conf /
COPY make-config-iso.sh /
COPY *.py /

EXPOSE 22 161/udp 830 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
