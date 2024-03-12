vrnetlab / Ekinops uCPE OneOS
===========================
This is the vrnetlab docker image for Ekinops uCPE platform running OneOS.

The hardware uCPE (and by extension the virtual uCPE) is a platform that can run
Virtual Network Functions (VNFs) to deliver services on the customers edge. We
have verified this vrnetlab image to work with Cisco Catalyst 8000v.

Building the docker image
-------------------------
Put the .qcow2 file in this directory and run `make docker-image` and you should
be good to go. The resulting image is called `vr-ucpe-oneos`. You can tag it
with something else if you want, like `my-repo.example.com/vr-ucpe-oneos` and
then push it to your repo. The tag is the same as the version of the uCPE image,
so if you have OneOS-OVP-X86_pi2-6.10.2m5_3.7.5 your final docker image will be
called vr-ucpe-ons:3.7.5

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to boot and respond to SSH / NETCONF with:

 * 3.7.5 (OneOS-OVP-X86_pi2-6.10.2m5_3.7.5)
 * 3.8.1 (OneOS-OVP-X86_pi2-6.11.1m3_3.8.1)

Usage
-----
```
docker run -d --privileged --name my-ucpe vrnetlab/vr-ucpe-oneos:3.7.5
```

System requirements
-------------------
CPU: 2 core

RAM: 8GB

Disk: 4GB

License handling
----------------
A license is required to deploy a VNF. uCPE has different types of licenses, but
specifically for VNFs you need to acquire an `open-virtualization` type license.
The license is tied to UUID. Once you have acquired the license key you can
provide it and the UUID to the bootstrap script with the following command:

```
docker run -d --privileged --name my-ucpe vrnetlab/vr-ucpe-oneos:3.7.5 --license-key <license-key> --uuid <uuid>
```

You can also provide multiple license keys and features to activate. The
parameter for feature activation is called `--license-activate`. For example, to
activate both the `open-virtualization` and `performance` features you would use
the following command:

```
docker run -d --privileged --name my-ucpe vrnetlab/vr-ucpe-oneos:3.7.5 --license-key <license-key> --uuid <uuid> --license-activate open-virtualization --license-activate performance
```

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: We use it in our labs in combination with Cisco C8000v and it works well. We
   have not tested it with any other VNFs. 
