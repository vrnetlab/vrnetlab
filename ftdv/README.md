# vrnetlab / Cisco FTDv

This is the vrnetlab docker image for Cisco FTDv.

## Building the docker image

Download the FTDv KVM install package from https://software.cisco.com/download/home/286306503/type/286306337. A valid service contract associated with your Cisco.com profile is required.

Put the `.qcow2` file in this directory and run `make` and you should be good to go. The resulting image is called `vrnetlab/vr-ftdv`.

It's been tested to boot, respond to SSH and have correct interface mapping
with the following images:

* Cisco_Secure_Firewall_Threat_Defense_Virtual-7.2.5-208.qcow2

## Usage

```
docker run -d --privileged --name <container_name> vrnetlab/vr-ftdv:<tag> --username <username> --password <password>
```

Where:

* `container_name` - name of the created container.
* `tag`- FTDv version (e.g., 7.2.5).
* `username`, `password` - FTDv credentials.

Example:

```
docker run -d --privileged --name my-ftdv vrnetlab/vr-ftdv:7.2.5 --username admin --password Admin123!
```

It will take about 1-2 minutes for the container to boot. After that, you can try to ssh to the container's IP or telnet to port 5000 for console access.

To obtain the container's IP run:

```
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container_name>
```

## System requirements

CPU: 4 core  
RAM: 8GB  
Disk: 4.6GB (Thin Provision disk size is 48.24GB)  
