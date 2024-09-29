# Cisco vIOS

This is the vrnetlab docker image for Cisco vIOS router.

## Justification

Cisco vIOS is a virtual router that can be used for testing and development purposes.
It is older than IOS XE and IOS XR (running only 15.x IOS version), however, it has several advantages:

- Small memory footprint (512MB vs 4GB+ for IOS XE/XR). With KSM enabled, the memory usage can be even lower.
- Easy to run on a laptop or a small server with limited resources for education purposes.
- Good for scalability testing of applications, when you don't need all new features of IOS XE/XR.

## Building the docker image

Qemu disk image can be obtained from Cisco Modeling Labs (CML).
More information about Cisco vIOS:
<https://developer.cisco.com/docs/modeling-labs/iosv/#iosv>

Once you extract disk image, format the name to the following format:
`cisco_vios-[VERSION].qcow2`
Where `[VERSION]` is the desired version of the image, for example `15.6.3M1`.

Finally, you can build the docker image with the `make docker-image` command.

Tested with versions:

- 15.9.3M6

## System requirements

- CPU: 1 core
- RAM: 512MB
- Disk: <1GB

## Network interfaces

The router supports up to 16 GigabitEthernet interfaces.

- The first interface `GigaEthernet0/0` is used as the management interface (it is placed in separated VRF).
- The rest of the interfaces are numbered from `GigaEthernet0/1` and are used as data interfaces.
  They are mapped to the docker container interfaces `eth1`, `eth2`, etc.

## Management plane

The following protocols are enabled on the management interface:

- CLI SSH on port 22
- NETCONF via SSH on port 22 (the same credentials are used as for CLI SSH)
- SNMPv2c on port 161 (`public` used as community string)

## Environment variables

| ID              | Description               | Default    |
|-----------------|---------------------------|------------|
| USERNAME        | SSH username              | vrnetlab   |
| PASSWORD        | SSH password              | VR-netlab9 |
| HOSTNAME        | device hostname           | vios       |
| TRACE           | enable trace logging      | false      |
| CONNECTION_MODE | interface connection mode | tc         |

## Configuration persistence

The startup configuration can be provided by mounting a file to `/config/startup-config.cfg`.
The changes done in the router configuration during runtime are not automatically persisted outside
the container - after stopping the container, the content of the flash/NVRAM is lost.
User is responsible for persistence of the changes, for example, by copying the configuration
to mounted startup-configuration file.

## Sample containerlab topology

```yaml
name: vios-lab

topology:
  kinds:
    linux:
      image: vrnetlab/vr-vios:15.9.3M6
      env:
        USERNAME: admin
        PASSWORD: admin
  nodes:
    vios1:
      kind: linux
      binds:
        - vios1.cfg:/config/startup-config.cfg
      env:
        HOSTNAME: xrv1
    vios2:
      kind: linux
      binds:
        - vios2.cfg:/config/startup-config.cfg
      env:
        HOSTNAME: xrv2
  links:
    - endpoints: ["vios1:eth1","vios2:eth1"]
```
