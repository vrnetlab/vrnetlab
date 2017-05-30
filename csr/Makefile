# match versions like:
# csr1000v-universalk9.16.03.01a.qcow2
# csr1000v-universalk9.16.04.01.qcow2
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9]\+\.[0-9]\+\.[0-9]\+[sb]\?\?\)\([^0-9].*\|$$\)/\1/')

-include ../makefile-sanity.include
-include ../makefile.include


usage:
	@echo "Usage: put the Cisco CSR1000v qcow2 image in this directory and run:"
	@echo "  make"

no-image:
	@echo "ERROR: you have no .qcow2 image"

docker-pre-build:
	-cat cidfile | xargs --no-run-if-empty docker rm -f
	-rm cidfile

docker-build: docker-build-common
	docker run --cidfile cidfile --privileged $(REGISTRY)vr-$(VR_NAME):$(VERSION) --trace --install
	docker commit --change='ENTRYPOINT ["/launch.py"]' $$(cat cidfile) $(REGISTRY)vr-$(VR_NAME):$(VERSION)
	docker rm -f $$(cat cidfile)
