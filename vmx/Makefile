NUM_IMAGES=$(shell ls *.tgz 2>/dev/null| wc -l)
IMAGE=$(shell ls *.tgz 2>/dev/null)
VERSION=$(shell echo $(IMAGE) | sed -e 's/.\+[^0-9]\([0-9][0-9]\.[0-9][A-Z][0-9]\+\.[0-9]\+\)[^0-9].*$$/\1/')

all: docker-image

usage:
	@echo "Usage: put the Juniper vMX .tgz file in this directory and run:"
	@echo "  make docker-image"

no-image:
	@echo "ERROR: you have no .tgz file"

more-than-one-image:
	@echo "ERROR: you have more than one .tgz file"

incorrect-version-string:
	@echo "ERROR: the .tgz file doesn't seem to contain a valid version number"
	@echo "       expecting [0-9][0-9].[0-9]R[0-9]+.[0-9]+"

ifeq ($(NUM_IMAGES), 0)
docker-image: no-image usage
else ifeq ($(NUM_IMAGES), 1)

ifeq ($(VERSION), $(IMAGE))
docker-image: incorrect-version-string
else
docker-image: docker-build
endif

else
docker-image: more-than-one-image usage
endif

docker-build:
	@echo "Building docker image using $(IMAGE) as vr-vmx:$(VERSION)"
	docker build -t vr-vmx:$(VERSION) .
