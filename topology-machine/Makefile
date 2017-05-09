all:
	docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(DOCKER_REGISTRY)topomachine .

docker-push:
	docker push $(DOCKER_REGISTRY)topomachine
