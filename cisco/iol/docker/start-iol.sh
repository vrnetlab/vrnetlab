#!/bin/bash

# Function to generate a random MAC address in the format aaaa.bbbb.cccc
generate_random_mac() {
    hexchars="0123456789abcdef"
    bbbb=$( for i in {1..4}; do echo -n ${hexchars:$(( $RANDOM % 16 )):1}; done )
    cccc=$( for i in {1..4}; do echo -n ${hexchars:$(( $RANDOM % 16 )):1}; done )
    echo "aaaa.${bbbb}.${cccc}"
}

# Function to create IOUYAP and NETMAP configurations
create_iouyap_and_netmap() {
    local base_port=49000
    local iouyap_file="/opt/iol/iouyap.ini"
    local netmap_file="/opt/iol/NETMAP"
    local config_file="/opt/iol/config.txt"
    local interfaces_text=""

    # Initialize the IOUYAP config
    echo "[default]" > $iouyap_file
    echo "base_port = $base_port" >> $iouyap_file
    echo "netmap = $netmap_file" >> $iouyap_file                                   

    # Initialize the NETMAP file
    > $netmap_file

    # Loop over each available eth interface and create the configuration
    for eth in $(ls /sys/class/net | grep eth); do
        # Extract the number from the eth interface name
        index=$(echo $eth | grep -o -E '[0-9]+')

        # Calculate the group and port
        local group=$((index / 4))  # Integer division to get the group
        local port=$((index % 4))   # Remainder to get the port

        echo "[513:${group}/${port}]" >> $iouyap_file
        echo "eth_dev = $eth" >> $iouyap_file
        echo "1:${group}/${port} 513:${group}/${port}" >> $netmap_file

        # Generate a random MAC address for each eth interface
        new_mac=$(generate_random_mac)
        
        if [[ $eth == "eth0" ]]; then
            # Replace <eth0_mac> with the generated MAC address for eth0
            sed -i "s/<eth0_mac>/mac-address ${new_mac}/" $config_file
        else
            # Generate the interface configuration text for other eth interfaces
            interfaces_text+="interface Ethernet ${group}/${port}\n mac-address ${new_mac}\n!\n"
        fi
    done

    # Replace <interfaces> in config.txt with the generated interface text
    sed -i "/<interfaces>/c\\${interfaces_text}" $config_file
}

# Create IOUYAP and NETMAP configurations
create_iouyap_and_netmap

# Run IOUYAP
sh -c "/usr/bin/iouyap 513 -q" &

# Get the highest numbered eth interface
max_eth=$(ls /sys/class/net | grep eth | grep -o -E '[0-9]+' | sort -n | tail -1)

# Calculate the number of groups of 4 interfaces
num_groups=$(( (max_eth + 4) / 4 ))

# Run the IOL image with the NETMAP file
export IOURC=/opt/iol/.iourc
set -x
exec /opt/iol/iol.bin 1 -e $num_groups -s 0 -d 0 -c config.txt -- -n 1024 -q -m 1024
