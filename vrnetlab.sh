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
		if [ -x $(command -v sshpass) ]; then
			sshpass -p VR-netlab9 ssh -oStrictHostKeyChecking=no $VR_ADDRESS -l vrnetlab
		else
			ssh -oStrictHostKeyChecking=no $VR_ADDRESS -l vrnetlab
		fi
	else
		ssh -oStrictHostKeyChecking=no $VR_ADDRESS -l $USER
	fi
}

vrsftp() {
        VROUTER=$1
        USER=$2
        VR_ADDRESS=$(vr_mgmt_ip $VROUTER)

        if [ -z "$USER" ] ; then
                if [ -x $(command -v sshpass) ]; then
                        sshpass -p VR-netlab9 sftp  vrnetlab@$VR_ADDRESS
                else
                        sftp vrnetlab@$VR_ADDRESS
                fi
        else
                sftp $USER@$VR_ADDRESS
        fi
}

vrcons() {
	VROUTER=$1
	telnet $(vr_mgmt_ip $VROUTER) 5000
}

vrbridge() {
	VR1=$1
	VP1=$2
	VR2=$3
	VP2=$4

	docker run -d  --name "bridge-${VR1}-${VP1}-${VR2}-${VP2}" --link $VR1 --link $VR2 vr-xcon --p2p "${VR1}/${VP1}--${VR2}/${VP2}"
}
