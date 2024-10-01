FROM public.ecr.aws/docker/library/debian:bookworm-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    iproute2 \
    iputils-ping \
    net-tools \
    sudo \
    gnupg \
    supervisor \
    && apt-get clean

# Add the GNS3 PPA for IOUYAP
RUN echo "deb http://ppa.launchpad.net/gns3/ppa/ubuntu trusty main" >> /etc/apt/sources.list
RUN apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 9A2FD067A2E3EF7B

# Update and install IOUYAP
RUN apt-get update && \
    apt-get install -y iouyap

# Set working directory
WORKDIR /opt/iol

# Add the IOL image and config files
COPY *.bin /opt/iol/iol.bin
COPY config.txt /opt/iol/config.txt

# Copy the supervisor file
COPY supervisord.conf /etc/supervisord.conf

# Copy the iourc file.
COPY .iour[c] /opt/iol/.iourc

# Copy the start-iol.sh script
COPY start-iol.sh /opt/iol/start-iol.sh

# Make the IOL image and script executable
RUN chmod +x /opt/iol/iol.bin
RUN chmod +x /opt/iol/start-iol.sh

# Copy the entrypoint script
COPY entrypoint.sh /opt/iol/entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /opt/iol/entrypoint.sh

# Set the entrypoint
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
