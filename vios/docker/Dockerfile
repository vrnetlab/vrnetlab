FROM public.ecr.aws/docker/library/debian:bookworm-slim
LABEL org.opencontainers.image.authors="xtothj@gmail.com"

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
   && apt-get install -y --no-install-recommends \
   bridge-utils \
   iproute2 \
   python3 \
   socat \
   qemu-kvm \
   qemu-utils \
   tcpdump \
   && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE* /
COPY *.py /

EXPOSE 22 161/udp 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]
