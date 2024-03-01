# vrnetlab / Fortinet FortiOS v7

=======================
Experimental support for the Fortinet FortiOS launched by containerlab.

## Building the docker image

Add your qcow2 image to the root of this folder.
Naming format: fortios-vX.Y.Z.qcow2

`make docker-build-fortigate`

## Running the docker image manually

If you need to run the image without using containerlab:

`make docker-run-fortigate`
