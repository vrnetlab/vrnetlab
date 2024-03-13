VENDOR=Fortigate
IMAGE_FORMAT=qcow2
IMAGE_GLOB=*.qcow2
-include ../makefile-sanity.include
-include ../makefile.include
IMAGE=$(shell find . -type f -iname *.qcow2 | head -n1 | cut -c3- )
VERSION=$(shell echo $(IMAGE) | sed 's|^fortios-v||' | sed -e 's/\.qcow2//')
.DEFAULT_GOAL=docker-build-fortigate
docker-build-fortigate:
	-rm -f docker/$(IMAGE) docker/healthcheck.py docker/vrnetlab.py
	cp $(IMAGE) docker
	cp ../common/* docker/
	@echo "Building docker image using $(IMAGE) as $(REGISTRY)vr-$(VR_NAME):$(VERSION)"
	(cd docker; docker build --build-arg IMAGE=$(IMAGE) --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(REGISTRY)vr-$(VR_NAME):$(VERSION) .)
	-rm -f docker/$(IMAGE) docker/healthcheck.py docker/vrnetlab.py

docker-run-fortigate:
	docker run -it -d --privileged --rm $(REGISTRY)vr-$(VR_NAME):$(VERSION) 
