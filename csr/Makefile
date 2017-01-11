# match versions like:
# csr1000v-universalk9.16.03.01a.qcow2
# csr1000v-universalk9.16.04.01.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\+\.[0-9]\+\.[0-9]\+[sb]\?\?\)\([^0-9].*\|$$\)/\1/')

-include ../makefile.include


usage:
	@echo "Usage: put the Cisco CSR1000v qcow2 image in this directory and run:"
	@echo "  make"

docker-build: docker-clean-build docker-pre-build
	@if [ -z "$$IMAGE" ]; then echo "ERROR: No IMAGE specified"; exit 1; fi
	@if [ "$(IMAGE)" = "$(VERSION)" ]; then echo "ERROR: Incorrect version string"; exit 1; fi
	@echo "Building docker image using $(IMAGE) as $(REGISTRY)vr-$(VR_NAME):$(VERSION)"
	cp ../common/* docker/
	cp $(IMAGE)* docker/
	(cd docker; docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) --build-arg IMAGE=$(IMAGE) -t $(REGISTRY)vr-$(VR_NAME):$(VERSION) .)
	docker run --privileged --name vr-temp $(REGISTRY)vr-$(VR_NAME):$(VERSION) --trace --install
	docker commit --change='ENTRYPOINT ["/launch.py"]' vr-temp $(REGISTRY)vr-$(VR_NAME):$(VERSION)
	docker rm vr-temp

no-image:
	@echo "ERROR: you have no .qcow2 image"
