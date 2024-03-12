-include ../makefile-sanity.include

all:
	docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(REGISTRY)topomachine .

docker-push:
	docker push $(REGISTRY)topomachine

ifeq ($(PNS),)
PNS:=$(shell whoami | sed 's/[^[:alnum:]._-]\+/_/g')
endif
CNT_PREFIX?=$(PNS)-topomachine
VOLUME_NAME?=$(CNT_PREFIX)-data

docker-test:
# Do the (awkward) volume-copy dance to make sure we can run this test in GitLab
# CI where the test script runs in a container with the hosts
# /var/run/docker.sock mounted - sibling container.
	-docker rm -f $(CNT_PREFIX)
	-docker volume rm $(VOLUME_NAME)
	docker volume create $(VOLUME_NAME)
	docker create -v $(VOLUME_NAME):/data --name $(CNT_PREFIX) busybox
	for f in example*; do docker cp $$f $(CNT_PREFIX):/data; done
	docker rm $(CNT_PREFIX)
	docker run -v $(VOLUME_NAME):/data --rm $(REGISTRY)topomachine --build example-hltopo.json
	docker run -v $(VOLUME_NAME):/data --rm $(REGISTRY)topomachine --run example-lltopo.json --dry-run
	docker run -v $(VOLUME_NAME):/data --rm $(REGISTRY)topomachine --template example-lltopo.json example.template

docker-test-clean:
	docker volume rm $(VOLUME_NAME)

docker-test-save-logs:
# nothing to do
