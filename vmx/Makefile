VENDOR=Juniper
NAME=vMX
IMAGE_FORMAT=tgz
IMAGE_GLOB=*.tgz

# match versions like:
# TODO: add example file names here
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9][0-9]\.[0-9][A-Z][0-9]\+\.[0-9]\+\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

docker-pre-build:
	-cat cidfile | xargs --no-run-if-empty docker rm -f
	-rm cidfile

docker-build: docker-build-common
	docker run --cidfile cidfile --privileged $(REGISTRY)vr-$(VR_NAME):$(VERSION) --trace --install
	docker commit --change='ENTRYPOINT ["/launch_vmx.py"]' $$(cat cidfile) $(REGISTRY)vr-$(VR_NAME):$(VERSION)
	docker rm -f $$(cat cidfile)
