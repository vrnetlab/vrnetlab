ARG REGISTRY=vrnetlab/
FROM golang:stretch as builder

RUN apt-get update -qy \
 && apt-get install -y git

RUN go get github.com/cloudflare/gortr/cmd/gortr

FROM ${REGISTRY}vr-xcon

COPY --from=builder /go/bin/gortr /

ADD roas.json /roas.json
ADD vr-gortr.py /vr-gortr.py

ENTRYPOINT ["/vr-gortr.py"]
