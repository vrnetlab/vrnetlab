VENDOR=Juniper
NAME=vMX
IMAGE_FORMAT=tgz
IMAGE_GLOB=*.tgz

# match versions like:
# vmx-14.1R6.4.tgz
# vmx-15.1F4.15.tgz
# vmx-bundle-15.1F6.9.tgz
# vmx-bundle-16.1R1.7.tgz
# vmx-bundle-16.1R2.11.tgz
# vmx-bundle-17.1R1.8.tgz
# vmx-bundle-16.1R4-S2.2.tgz
# vmx-bundle-17.1R1-S1.tgz
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9][0-9]\.[0-9][A-Z][0-9]\+\(\.[0-9]\+\|-S[0-9]\+\(\.[0-9]\+\)\?\)\)[^0-9].*$$/\1/')

-include ../makefile-sanity.include
-include ../makefile.include

docker-pre-build:
	-cat cidfile | xargs --no-run-if-empty docker rm -f
	-rm cidfile

docker-build: docker-build-common
	docker run --cidfile cidfile --privileged $(REGISTRY)vr-$(VR_NAME):$(VERSION) --trace --install
	docker commit --change='ENTRYPOINT ["/launch_vmx.py"]' $$(cat cidfile) $(REGISTRY)vr-$(VR_NAME):$(VERSION)
	docker rm -f $$(cat cidfile)
