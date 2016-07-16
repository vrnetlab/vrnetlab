NUM_IMAGES=$(shell ls *.vmdk* 2>/dev/null| wc -l)
IMAGE=$(shell ls *.vmdk* 2>/dev/null)
VERSION=$(shell echo $(IMAGE) | sed -e 's/.*\([0-9]\.[0-9]\.[0-9]\).*/\1/')

all: docker-image

usage:
	@echo "Usage: put the Cisco IOS XRv vmdk image in this directory and run:"
	@echo "  make docker-image"

no-image:
	@echo "ERROR: you have no .vmdk image"

more-than-one-image:
	@echo "ERROR: you have more than one .vmdk image"

ifeq ($(NUM_IMAGES), 0)
docker-image: no-image usage
else ifeq ($(NUM_IMAGES), 1)
docker-image: docker-build
else
docker-image: more-than-one-image usage
endif

docker-build:
	@echo "Building docker image using $(IMAGE) as vr-xrv:$(VERSION)"
	docker build -t vr-xrv:$(VERSION) .
