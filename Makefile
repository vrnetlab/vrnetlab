VRS = sros vmx xrv
VRS_PUSH = $(VRS:=-push)

.PHONY: $(VRS) $(VRS_PUSH)

all: $(VRS)

$(VRS):
	cd $@; $(MAKE)

docker-push: $(VRS_PUSH)

$(VRS_PUSH):
	cd $(@:-push=); $(MAKE) docker-push
