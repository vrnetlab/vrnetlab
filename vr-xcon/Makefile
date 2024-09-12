-include ../makefile-sanity.include

all:
	docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(REGISTRY)vr-xcon .

docker-push:
	docker push $(REGISTRY)vr-xcon

ifeq ($(PNS),)
PNS:=$(shell whoami | sed 's/[^[:alnum:]._-]\+/_/g')
endif

CNT_PREFIX?=xcon-test-$(PNS)

docker-test:
# This test sets up two enpoint containers using the vr-xcon container image.
# Each endpoint has two sidecar containers where vr-xcon is used to create a
# tap0 and tap1 interfacea with the provided IP address and a listening socket
# 10001 and 10002 for stitching. Then we connect the two endpoints with xcon.py
# and xcon-ng and verify the links work with ping.
	docker network create $(CNT_PREFIX)
	docker run -td --name $(CNT_PREFIX)-ep1 --network $(CNT_PREFIX) --network-alias ep1 --entrypoint /bin/sh $(REGISTRY)vr-xcon -c "tail -f /dev/null"
	docker run -d --name $(CNT_PREFIX)-ep1-tap0 --privileged --network container:$(CNT_PREFIX)-ep1 $(REGISTRY)vr-xcon --tap-if tap0 --tap-listen 1 --ipv4-address 10.0.0.1/30
	docker run -d --name $(CNT_PREFIX)-ep1-tap1 --privileged --network container:$(CNT_PREFIX)-ep1 $(REGISTRY)vr-xcon --tap-if tap1 --tap-listen 2 --ipv4-address 10.1.0.1/30
	docker run -td --name $(CNT_PREFIX)-ep2 --network $(CNT_PREFIX) --network-alias ep2 --entrypoint /bin/sh $(REGISTRY)vr-xcon -c "tail -f /dev/null"
	docker run -d --name $(CNT_PREFIX)-ep2-tap0 --privileged --network container:$(CNT_PREFIX)-ep2 $(REGISTRY)vr-xcon --tap-if tap0 --tap-listen 1 --ipv4-address 10.0.0.2/30
	docker run -d --name $(CNT_PREFIX)-ep2-tap1 --privileged --network container:$(CNT_PREFIX)-ep2 $(REGISTRY)vr-xcon --tap-if tap1 --tap-listen 2 --ipv4-address 10.1.0.2/30
	docker run -d --name $(CNT_PREFIX)-xcon --privileged --network $(CNT_PREFIX) $(REGISTRY)vr-xcon --p2p ep1/1--ep2/1 --debug
	docker run -d --name $(CNT_PREFIX)-xcon-ng --privileged --network $(CNT_PREFIX) --entrypoint /xcon $(REGISTRY)vr-xcon --p2p ep1/2--ep2/2 --trace
	docker exec $(CNT_PREFIX)-ep1 ping -c1 10.0.0.2
	docker exec $(CNT_PREFIX)-ep1 ping -c1 10.1.0.2

docker-test-clean:
	docker ps -aqf name=$(CNT_PREFIX) | xargs --no-run-if-empty docker rm -f
	-docker network rm $(CNT_PREFIX)

docker-test-save-logs:
	for cnt in `docker ps -af name=$(CNT_PREFIX) --format '{{.Names}}'`; do \
		docker logs $${cnt} > $${cnt}.log 2>&1; \
	done
