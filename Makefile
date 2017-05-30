VRS = vr-xcon vr-bgp csr nxos sros veos vmx vqfx xrv
VRS_PUSH = $(VRS:=-push)

.PHONY: all $(VRS) $(VRS_PUSH)

all: $(VRS)

$(VRS):
	cd $@; $(MAKE)

docker-push: $(VRS_PUSH)

$(VRS_PUSH):
	cd $(@:-push=); $(MAKE) docker-push
