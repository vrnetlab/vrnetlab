-include ../makefile-sanity.include

all:
	docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(REGISTRY)topomachine .

docker-push:
	docker push $(REGISTRY)topomachine
