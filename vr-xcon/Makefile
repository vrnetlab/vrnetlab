-include ../makefile-sanity.include

all:
	docker build --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) -t $(REGISTRY)vr-xcon .

docker-push:
	docker push $(REGISTRY)vr-xcon

docker-test:
	@echo "TODO: implement smoke test"

docker-test-clean:
	@echo "TODO: implement smoke test"

docker-test-save-logs:
	@echo "TODO: implement smoke test"
