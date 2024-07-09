# Cisco Catalyst 9000V

This is the vrnetlab image for the Cisco Catalyst 9000v (cat9kv, c9000v).

The Cat9kv emulates two types of ASICs that are found in the common Catalyst 9000 hardware platforms, either:

- UADP (Cisco Unified Access Data Plane)
- Cisco Silicon One Q200 (referred to as Q200 for short)

The Q200 is a newer ASIC, however doen't support as many features as the UADP ASIC emulation.

> Insufficient RAM will not allow the node to boot correctly.

Eight interfaces will always appear regardless if you have defined any links in the `*.clab.yaml` topology file. The Cat9kv requires 8 interfaces at minimum to boot, so dummy interfaces are created if there are an insufficient amount of interfaces (links) defined.

## Building the image

Copy the Cat9kv .qcow2 file in this directory and you can perform `make docker-image`. On average the image takes approxmiately ~4 minutes to build as an initial install process occurs.

The UADP and Q200 use the same .qcow2 image. The default image created is the UADP image.

To configure the Q200 image or enable a higher throughput dataplane for UADP; you must supply the relevant `vswitch.xml` file. You can place that file in this directory and build the image.

> You can obtain a `vswitch.xml` file from the relevant CML node definiton file.

Known working versions:

- cat9kv-prd-17.12.01prd9.qcow2 (UADP & Q200)

## Usage

You can define the image easily and use it in a topolgy. As mentioned earlier no links are requried to be defined.

```yaml
# topology.clab.yaml
name: mylab
topology:
  nodes:
    cat9kv:
      kind: cisco_cat9kv
      image: vrnetlab/vr-cat9kv:<tag>
```

You can also supply a vswitch.xml file using `binds`. Below is an example topology file.

```yaml
# topology.clab.yaml
name: mylab
topology:
  nodes:
    cat9kv:
      kind: cisco_cat9kv
      image: vrnetlab/vr-cat9kv:<tag>
      binds:
        - /path/to/vswitch.xml:/vswitch.xml
```

### Interface naming

Currently a maximum of 8 data-plane interfaces are supported. 9 interfaces total if including the management interface.

- `eth0` - Node management interface
- `eth1` - First dataplane interface (GigabitEthernet1/0/1).
- `ethX` - Subsequent dataplane interfaces will count onwards from 1. For example, the third dataplane interface will be `eth3`

You can also use interface aliases of `GigabitEthernet1/0/x` or `Gi1/0/x`

### Environment Variables

| Environment Variable  | Default       |
| --------------------- | ------------- |
| VCPU                  | 4             |
| RAM                   | 18432         |

### Example

```yaml
name: my-example-lab
topology:
  nodes:
    my-cat9kv:
      kind: cisco_cat9kv
      image: vrnetlab/vr-cat9kv:17.12.01
    env:
        VCPU: 6
        RAM: 12288
```

## System requirements

|           | UADP (Default)| Q200  |
| --------- | ------------- | ----- |
| vCPU      | 4             | 4     |
| RAM (MB)  | 18432         | 12288 |
| Disk (GB) | 4             | 4     |
