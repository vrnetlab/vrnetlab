#!/bin/sh

vr_mgmt_ip() { 
	VROUTER=$1
	VR_ADDRESS=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $VROUTER)
	echo $VR_ADDRESS
}

vrssh() {
	VROUTER=$1
	USER=$2
	VR_ADDRESS=$(vr_mgmt_ip $VROUTER)

	if [ -z "$USER" ] ; then
		ssh $VR_ADDRESS -l vrnetlab
	else
		ssh $VR_ADDRESS -l $USER
	fi
}

vrcons() {
	VROUTER=$1
	telnet $(vr_mgmt_ip $VROUTER) 5000
}
