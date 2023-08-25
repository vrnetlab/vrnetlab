FROM debian:bullseye
MAINTAINER Kristian Larsson <kristian@spritelink.net>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qy \
 && apt-get upgrade -qy \
 && apt-get install -y \
    python3-jinja2 \
    python3-yaml \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg2 \
    software-properties-common \
# Install git & make so that we can use topomachine in CI to check for uncommitted topology and scripts changes
    git \
    make \
 && curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - \
 && add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/debian \
   $(lsb_release -cs) \
   stable" \
 && apt-get update -qy \
 && apt-get -y install docker-ce \
 && rm -rf /var/lib/apt/lists/*

ADD topomachine /usr/local/bin
ADD *example* /data/

ENTRYPOINT ["/usr/local/bin/topomachine"]
