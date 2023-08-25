#!/bin/bash
# Create a config metadisk from a supplied juniper.conf to attach
# to a vJunos VM instance
usage() {
	echo "Usage :  make-config.sh <juniper-config> <config-disk>"
	exit 0;
}
cleanup () {
	echo "Cleaning up..."
	umount -f -q $MNTDIR
	losetup -d $LOOPDEV
	rm -rfv $STAGING
	rm -rfv $MNTDIR
}

cleanup_failed () {
	cleanup;
	rm -rfv $2
	exit 1
}

if [ $# != 2 ]; then
	usage;
fi


STAGING=`mktemp -d -p /var/tmp`
MNTDIR=`mktemp -d -p /var/tmp`
mkdir $STAGING/config
cp -v $1 $STAGING/config
qemu-img create -f qcow2 $2 1M
LOOPDEV=`losetup --show -f $2`
if [ $? != 0 ]; then
	cleanup_failed;
fi
mkfs.vfat  -v -n "vmm-data" $LOOPDEV
if [ $? != 0 ]; then
	echo "Failed to format disk $LOOPDEV; exiting"
	cleanup_failed;
fi
mount -t vfat $LOOPDEV $MNTDIR
if [ $? != 0 ]; then
		echo "Failed to mount metadisk $LOOPDEV; exiting"
	cleanup_failed;

fi
echo "Copying file(s) to config disk $2"
(cd $STAGING; tar cvzf $MNTDIR/vmm-config.tgz .)
cleanup
echo "Config disk $2 created"
exit 0
