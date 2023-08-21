-include ../makefile-sanity.include

all:
	docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(REGISTRY)topomachine .

docker-push:
	docker push $(REGISTRY)topomachine

docker-test:
	docker run --rm $(REGISTRY)topomachine --build example-hltopo.json
	docker run --rm $(REGISTRY)topomachine --run example-lltopo.json --dry-run
	docker run --rm $(REGISTRY)topomachine --template example-lltopo.json example.template

docker-test-clean:
# nothing to do

docker-test-save-logs:
# nothing to do
