FROM ubuntu:yakkety

RUN apt-get update \
 && apt-get install -y \
    curl \
	docker.io \
	make \
 && curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash \
 && apt-get install -y git-lfs \
 && rm -rf /var/lib/apt/lists/*
