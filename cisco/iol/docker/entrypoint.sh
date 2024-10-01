#!/bin/bash

# Function to update the configuration files
update_configs() {
    # Get the eth0 IP address
    eth0_ip=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
    eth0_ipv6=$( ip addr show eth0 | grep "inet6\b" | awk '{print $2}' | cut -d/ -f1 | sed -n '2p')
    # Get the default gateway IP address
    gateway_ip=$(ip route | grep default | awk '{print $3}')
    gateway_ipv6=$(ip -6 route | grep default | awk '{print $3}' | head -n 1)

    # Replace <hostname>, <ip_address>, and <ip_gateway> in config.txt
    sed -i "s/<hostname>/$HOSTNAME/g" /opt/iol/config.txt
    sed -i "s/<ip_address>/$eth0_ip/g" /opt/iol/config.txt
    sed -i "s/<ip_gateway>/$gateway_ip/g" /opt/iol/config.txt
    sed -i "s/<ipv6_address>/$eth0_ipv6/g" /opt/iol/config.txt
    sed -i "s/<ipv6_gateway>/$gateway_ipv6/g" /opt/iol/config.txt

}

# Function to flush eth0 IP address
flush_eth0_ip() {
    ip addr flush dev eth0
    ip -6 addr flush dev eth0
}

# Function to run the startup script after a delay
run_startup_script() {
    # Wait for 10 seconds to ensure eth0 is configured
    sleep 10

    # Update configuration files
    update_configs

    # Flush eth0 IP address
    flush_eth0_ip

    # Run the IOL image using the start-iol.sh script
    supervisorctl start iol
}

# Start the function in the background
run_startup_script &

# Start bash interactively
exec "$@"
