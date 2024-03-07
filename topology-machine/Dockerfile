FROM debian:bookworm
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    python3-jinja2 \
    python3-yaml \
    curl \
# Install git & make so that we can use topomachine in CI to check for uncommitted topology and scripts changes
    git \
    make \
 && install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
 && chmod a+r /etc/apt/keyrings/docker.asc \
 && echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
 && apt-get update \
 && apt-get -y install docker-ce \
 && rm -rf /var/lib/apt/lists/*

ADD topomachine /usr/local/bin
ADD *example* /data/

WORKDIR /data
ENTRYPOINT ["/usr/local/bin/topomachine"]
