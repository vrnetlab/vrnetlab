#!/bin/bash
# Create a config metadisk from a supplied juniper.conf to attach
# to a vSRX VM instance
usage() {
	echo "Usage :  make-config-iso.sh <juniper-config> <config-disk>"
	exit 0;
}
cleanup () {
	rm -rfv $STAGING
}

if [ $# != 2 ]; then
	usage;
fi


STAGING=`mktemp -d -p /var/tmp`
mkdir $STAGING/config
cp -v $1 $STAGING/config
mkisofs -l -o $2 $STAGING/config

cleanup
echo "Config disk $2 created"
exit 0
