ifdef DOCKER_REGISTRY
ifneq ($(DOCKER_REGISTRY), $(shell echo $(DOCKER_REGISTRY) | sed -ne '/^[A-Za-z0-9.]\+:[0-9]\+$$/p'))
$(error Bad docker registry URL. Should follow format registry.example.com:1234)
endif
    REGISTRY=$(DOCKER_REGISTRY)/
else
    REGISTRY=
endif

all:
	docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(REGISTRY)vr-bgp .

docker-push:
	docker push $(REGISTRY)vr-bgp
