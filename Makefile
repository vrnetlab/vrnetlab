VRS = sros xrv

.PHONY: $(VRS)

all: $(VRS)

$(VRS):
	cd $@; $(MAKE)
