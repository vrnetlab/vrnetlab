FROM debian:bullseye
LABEL org.opencontainers.image.authors="roman@dodin.dev"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
   && apt-get upgrade -qy \
   && apt-get install -y \
   bridge-utils \
   iproute2 \
   python3-ipy \
   socat \
   qemu-system-x86=1:5.2+dfsg-11+deb11u2 \
   qemu-utils=1:5.2+dfsg-11+deb11u2 \
   && rm -rf /var/lib/apt/lists/*

ARG IMAGE
COPY $IMAGE* /
COPY *.py /

EXPOSE 22 830 5000 10000-10099
HEALTHCHECK CMD ["/healthcheck.py"]
ENTRYPOINT ["/launch.py"]