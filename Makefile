IMAGES_DIR=
VRS = vr-xcon vr-bgp csr nxos nxos9kv routeros sros veos vmx vsr1000 vqfx vrp xrv xrv9k
VRS_PUSH = $(VRS:=-push)
VRS_TEST = $(VRS:=-test)

.PHONY: all $(VRS) $(VRS_PUSH) $(VRS_TEST)

all: $(VRS)

$(VRS):
ifneq ($(IMAGES_DIR),)
	cp -av $(IMAGES_DIR)/$@/* $@/
endif
	cd $@; $(MAKE)

docker-push: $(VRS_PUSH)

$(VRS_PUSH):
	cd $(@:-push=); $(MAKE) docker-push

$(VRS_TEST):
	cd $(@:-test=); $(MAKE) docker-test
