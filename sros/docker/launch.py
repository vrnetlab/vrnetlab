#!/usr/bin/env python3

import datetime
import logging
import os
import re
import shutil
import signal
import sys
from typing import Dict
from dataclasses import dataclass


import vrnetlab


def handle_SIGCHLD(signal, frame):
    os.waitpid(-1, os.WNOHANG)


def handle_SIGTERM(signal, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, handle_SIGTERM)
signal.signal(signal.SIGTERM, handle_SIGTERM)
signal.signal(signal.SIGCHLD, handle_SIGCHLD)

TRACE_LEVEL_NUM = 9
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


def trace(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kws)


logging.Logger.trace = trace


@dataclass
class SROSVersion:
    """SROSVersion is a dataclass that stores SROS version components

    version is a string repr of a version number, e.g. "22.10.R1"
    major, minor, patch are integers representing the version number components
    patch version that is typically in the form of R1, R2, etc. will be stripped to integer only
    """

    version: str
    major: int
    minor: int
    patch: int


# SROS_VERSION global variable is used to store the SROS version components
SROS_VERSION = SROSVersion(version="", major=0, minor=0, patch=0)


# line_card_config is a convenience function that generates line card definition strings
def line_card_config(
    chassis: str, card: str, mda: str, integrated: bool = False, card_type: str = None
) -> Dict[str, str]:
    """
    line_card_config is a convenience function that generates line card definition strings
    such as `timos_line`, `card_config`.
    """
    slot: str = "A" if integrated else "1"
    return {
        "timos_line": f"slot={slot} chassis={chassis} card={card} mda/1={mda}",
        "card_config": f"""
/configure card 1 card-type {card_type if card_type else card}
/configure card 1 mda 1 mda-type {mda}
      """,
    }


SROS_VARIANTS = {
    "ixr-e-big": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 34,  # 24*10 + 8*25G + 2*100G (with connector)
        "cp": {
            "min_ram": 3,
            "timos_line": "slot=A chassis=ixr-e card=cpm-ixr-e",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 4,
                **line_card_config(
                    chassis="ixr-e",
                    card="imm24-sfp++8-sfp28+2-qsfp28",
                    mda="m24-sfp++8-sfp28+2-qsfp28",
                ),
            }
        ],
    },
    #    "ixr-6": {
    #        "deployment_model": "distributed",
    #        # control plane (CPM)
    #        "max_nics": 36,
    #        "cp": {
    #            "min_ram": 3,
    #            "timos_line": "slot=A chassis=ixr-6 card=cpm-ixr",
    #        },
    #        # line card (IOM/XCM)
    #        "lc": {
    #            "min_ram": 6,
    #            "timos_line": "chassis=ixr-6 slot=1 card=imm36-100g-qsfp28 mda/1=m36-100g-qsfp28",
    #            "card_config": """/configure chassis router chassis-number 1 power-module 1 power-module-type ixr-dc-3000
    #            /configure chassis router chassis-number 1 power-module 2 power-module-type ixr-dc-3000
    #            /configure chassis router chassis-number 1 power-module 3 power-module-type ixr-dc-3000
    #            /configure chassis router chassis-number 1 power-module 4 power-module-type ixr-dc-3000
    #            /configure chassis router chassis-number 1 power-module 5 power-module-type ixr-dc-3000
    #            /configure chassis router chassis-number 1 power-module 6 power-module-type ixr-dc-3000
    #            /configure card 1 card-type imm36-100g-qsfp28
    #            /configure card 1 mda 1 mda-type m36-100g-qsfp28
    #            """,
    #        },
    #    },
    "ixr-r6": {
        "deployment_model": "integrated",
        "cpu": 4,
        "min_ram": 6,  # minimum RAM requirements
        "max_nics": 7,
        **line_card_config(
            chassis="ixr-r6",
            card="cpiom-ixr-r6",
            card_type="iom-ixr-r6",
            mda="m6-10g-sfp++1-100g-qsfp28",  # Supports MACsec
            integrated=True,
        ),
    },
    "ixr-s": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 54,
        "cp": {
            "min_ram": 3,
            "timos_line": "slot=A chassis=ixr-s card=cpm-ixr-s",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 4,
                "timos_line": "chassis=ixr-s slot=1 card=imm48-sfp++6-qsfp28 mda/1=m48-sfp++6-qsfp28",
                "card_config": """/configure card 1 card-type imm48-sfp++6-qsfp28
            /configure card 1 mda 1 mda-type m48-sfp++6-qsfp28
            """,
            }
        ],
    },
    "ixr-e-small": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 18,
        "cp": {
            "min_ram": 3,
            "timos_line": "slot=A chassis=ixr-e card=imm14-10g-sfp++4-1g-tx",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 4,
                "timos_line": "chassis=ixr-e slot=1 card=imm14-10g-sfp++4-1g-tx mda/1=m14-10g-sfp++4-1g-tx",
                "card_config": """
            """,
            }
        ],
    },
    "ixr-ec": {
        "deployment_model": "integrated",
        "min_ram": 4,  # minimum RAM requirements
        "max_nics": 30,
        **line_card_config(
            chassis="ixr-ec",
            card="cpm-ixr-ec",
            card_type="imm4-1g-tx+20-1g-sfp+6-10g-sfp+",
            mda="m4-1g-tx+20-1g-sfp+6-10g-sfp+",
            integrated=True,
        ),
    },
    "sr-1s": {
        "deployment_model": "integrated",
        "min_ram": 6,  # minimum RAM requirements
        "max_nics": 36,
        "timos_line": "chassis=sr-1s slot=A card=xcm-1s mda/1=s36-100gb-qsfp28",
        **line_card_config(
            chassis="sr-1s",
            card="cpm-1s",
            card_type="xcm-1s",
            mda="s36-100gb-qsfp28",
            integrated=True,
        ),
        "power": {"modules": {"ac/hv": 3, "dc": 4}},
    },
    "sr-1s-macsec": {
        "deployment_model": "integrated",
        "min_ram": 6,  # minimum RAM requirements xcm-1s
        "max_nics": 20,
        "timos_line": "slot=A chassis=sr-1s card=xcm-1s xiom/x1=iom-s-3.0t mda/x1/1=ms16-100gb-sfpdd+4-100gb-qsfp28",
        "card_config": """
        /configure card 1 card-type xcm-1s
        /configure card 1 xiom x1 xiom-type iom-s-3.0t level cr1600g+
        /configure card 1 xiom x1 mda 1 mda-type ms16-100gb-sfpdd+4-100gb-qsfp28
         """,
        "power": {"modules": {"ac/hv": 3, "dc": 4}},
    },
    "sr-2s": {
        "deployment_model": "distributed",
        "max_nics": 10,  # 8+2
        "power": {"modules": {"ac/hv": 3, "dc": 4}},
        "cp": {
            "min_ram": 3,
            # The 7750 SR-2s uses an integrated switch fabric module (SFM) design
            "timos_line": "slot=A chassis=sr-2s sfm=sfm-2s card=cpm-2s",
        },
        "lcs": [
            {
                "min_ram": 4,
                "timos_line": "slot=1 chassis=sr-2s sfm=sfm-2s card=xcm-2s xiom/x1=iom-s-3.0t mda/x1/1=ms8-100gb-sfpdd+2-100gb-qsfp28",
                "card_config": """
/configure sfm 1 sfm-type sfm-2s
/configure sfm 2 sfm-type sfm-2s
/configure card 1 card-type xcm-2s
/configure card 1 xiom x1 xiom-type iom-s-3.0t level cr1600g+
/configure card 1 xiom x1 mda 1 mda-type ms8-100gb-sfpdd+2-100gb-qsfp28
""",
            },
        ],
    },
    "sr-7s": {  # defaults to FP5 cards
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 36,
        "power": {"modules": 10, "shelves": 2},
        "cp": {
            "min_ram": 4,
            "timos_line": "slot=A chassis=SR-7s sfm=sfm2-s card=cpm2-s",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 6,
                "timos_line": "slot=1 chassis=SR-7s sfm=sfm2-s card=xcm2-7s mda/1=x2-s36-800g-qsfpdd-18.0t",
                "card_config": """
                /configure sfm 1 sfm-type sfm2-s
                /configure sfm 2 sfm-type sfm2-s
                /configure sfm 3 sfm-type sfm2-s
                /configure sfm 4 sfm-type sfm2-s
                /configure card 1 card-type xcm2-7s
                /configure card 1 mda 1 mda-type x2-s36-800g-qsfpdd-18.0t
                """,
            },
        ],
    },
    "sr-7s-fp4": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 36,
        "power": {"modules": 10, "shelves": 2},
        "cp": {
            "min_ram": 4,
            "timos_line": "slot=A chassis=SR-7s sfm=sfm-s card=cpm2-s",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 6,
                "timos_line": "slot=1 chassis=SR-7s sfm=sfm-s card=xcm-7s mda/1=s36-100gb-qsfp28",
                "card_config": """
                /configure sfm 1 sfm-type sfm-s
                /configure sfm 2 sfm-type sfm-s
                /configure sfm 3 sfm-type sfm-s
                /configure sfm 4 sfm-type sfm-s
                /configure sfm 5 sfm-type sfm-s
                /configure sfm 6 sfm-type sfm-s
                /configure sfm 7 sfm-type sfm-s
                /configure sfm 8 sfm-type sfm-s
                /configure card 1 card-type xcm-7s
                /configure card 1 mda 1 mda-type s36-100gb-qsfp28
                """,
            }
        ],
    },
    "sr-14s": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 36,
        "power": {"modules": 10, "shelves": 2},
        "cp": {
            "min_ram": 4,
            "timos_line": "slot=A chassis=SR-14s sfm=sfm-s card=cpm2-s",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 6,
                "timos_line": "slot=1 chassis=SR-14s sfm=sfm-s card=xcm-14s mda/1=s36-100gb-qsfp28",
                "card_config": """
                /configure sfm 1 sfm-type sfm-s
                /configure sfm 2 sfm-type sfm-s
                /configure sfm 3 sfm-type sfm-s
                /configure sfm 4 sfm-type sfm-s
                /configure sfm 5 sfm-type sfm-s
                /configure sfm 6 sfm-type sfm-s
                /configure sfm 7 sfm-type sfm-s
                /configure sfm 8 sfm-type sfm-s
                /configure card 1 card-type xcm-14s
                /configure card 1 mda 1 mda-type s36-100gb-qsfp28
            """,
            }
        ],
    },
    "sr-1": {
        "deployment_model": "integrated",
        "min_ram": 5,  # minimum RAM requirements
        "max_nics": 12,
        "timos_line": "chassis=sr-1 slot=A card=cpm-1 slot=1 mda/1=me12-100gb-qsfp28",
        **line_card_config(
            chassis="sr-1",
            card="cpm-1",
            card_type="iom-1",
            mda="me12-100gb-qsfp28",
            integrated=True,
        ),
    },
    "sr-1e": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 40,
        "cp": {
            "min_ram": 4,
            "timos_line": "slot=A chassis=sr-1e card=cpm-e",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 4,
                "timos_line": "chassis=sr-1e slot=1 card=iom-e mda/1=me40-1gb-csfp",
                **line_card_config(chassis="sr-1e", card="iom-e", mda="me40-1gb-csfp"),
            }
        ],
    },
    "sr-1e-sec": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 12,
        "cp": {
            "min_ram": 4,
            "timos_line": "slot=A chassis=sr-1e card=cpm-e",
        },
        # line card (IOM/XCM)
        "lc": {
            "min_ram": 4,
            "timos_line": "chassis=sr-1e slot=1 card=iom-e mda/1=me12-10/1gb-sfp+ mda/2=isa2-tunnel",
            "card_config": """/configure card 1 card-type iom-e
            /configure card 1 mda 1 mda-type me12-10/1gb-sfp+
            /configure card 1 mda 2 mda-type isa2-tunnel
            """,
        },
    },
    "sr-a4": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 10,
        "cp": {
            "min_ram": 4,
            "timos_line": "slot=A chassis=sr-a4 card=cpm-a",
        },
        # line card (IOM/XCM)
        "lc": {
            "min_ram": 4,
            **line_card_config(
                chassis="sr-a4", card="iom-a", mda="maxp10-10/1gb-msec-sfp+"
            ),
        },
    },
    "sr-1x-48d": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 48,
        "cp": {
            "min_ram": 4,
            "timos_line": "slot=A chassis=sr-1x-48D card=cpm-1x",
        },
        # line card (IOM/XCM)
        "lcs": [
            {
                "min_ram": 4,
                **line_card_config(
                    chassis="sr-1x-48D",
                    card="i48-800g-qsfpdd-1x",
                    mda="m48-800g-qsfpdd-1x",
                ),
            }
        ],
    },
    "vsr-i": {
        "deployment_model": "integrated",
        "min_ram": 8,  # minimum RAM requirements
        "max_nics": 20,
        "timos_line": "chassis=VSR-I slot=A card=iom-v mda/1=m20-v mda/2=isa-tunnel-v",
        "card_config": """/configure card 1 card-type iom-v
        /configure card 1 mda 1 mda-type m20-v
        /configure card 1 mda 2 mda-type isa-tunnel-v
        """,
        # depending of the Network Function the Multi-Service Integrated Services Module (MS-ISM) card could be also defined as:
        # isa-aa-v --> Application Assurance (Stateful Firewall)
        # isa-bb-v --> Broadband (BNG, LAC, LNS)
        # isa-tunnel-v (Already Configured) --> IP Tunneling (GRE, IPSec)
    },
}

# SR OS Classic CLI common configuration
SROS_CL_COMMON_CFG = """
/configure system name {name}
/configure system netconf no shutdown
/configure system security profile \"administrative\" netconf base-op-authorization lock
/configure system login-control ssh inbound-max-sessions 30
/configure system management-interface yang-modules no nokia-modules
/configure system management-interface yang-modules nokia-combined-modules
/configure system management-interface yang-modules no base-r13-modules
/configure system grpc allow-unsecure-connection
/configure system grpc gnmi auto-config-save
/configure system grpc gnmi no shutdown
/configure system grpc rib-api no shutdown
/configure system grpc no shutdown
/configure system netconf auto-config-save
/configure system netconf no shutdown
/configure system security profile "administrative" netconf base-op-authorization kill-session
/configure system security profile "administrative" netconf base-op-authorization lock
/configure system snmp packet-size 9216
/configure system snmp streaming no shutdown
/configure system snmp no shutdown
/configure system security user "admin" access netconf
/configure system security user "admin" access console
/configure system security user "admin" access grpc
/configure system security user "admin" access snmp
/configure system security user "admin" access ftp
"""

# SR OS Model-Driven CLI common configuration
SROS_MD_COMMON_CFG = """
/configure system name {name}
/configure system security aaa local-profiles profile administrative netconf base-op-authorization lock true
/configure system security aaa local-profiles profile "administrative" netconf base-op-authorization kill-session true
/configure system login-control ssh inbound-max-sessions 30
/configure system grpc admin-state enable
/configure system grpc allow-unsecure-connection
/configure system grpc gnmi auto-config-save true
/configure system grpc rib-api admin-state enable
/configure system management-interface netconf admin-state enable
/configure system management-interface netconf auto-config-save true
/configure system management-interface snmp packet-size 9216
/configure system management-interface snmp streaming admin-state enable
/configure system security user-params local-user user "admin" access console true
/configure system security user-params local-user user "admin" access ftp true
/configure system security user-params local-user user "admin" access snmp true
/configure system security user-params local-user user "admin" access netconf true
/configure system security user-params local-user user "admin" access grpc true
"""

# to allow writing config to tftp location we needed to spin up a normal
# tftp server in container host system. To access the host from qemu VM
# we needed to put SR OS management interface in the container host network namespace
# this is done by putting SR OS management interface with into a br-mgmt bridge
# the bridge and SR OS mgmt interfaces will be addressed as follows
BRIDGE_V4_ADDR = "172.31.255.29"
SROS_MGMT_V4_ADDR = "172.31.255.30"
V4_PREFIX_LENGTH = "30"
BRIDGE_V6_ADDR = "200::"
SROS_MGMT_V6_ADDR = "200::1"
V6_PREFIX_LENGTH = "127"


def parse_variant_line(cfg, obj, skip_nics=False):
    if not obj:
        obj = {}

    timos_line = []
    for elem in cfg.split():
        # skip cp: lc: markers
        if elem in ["cp:", "lc:"]:
            continue

        if "cpu=" in elem:
            obj["cpu"] = elem.split("=")[1]
            continue

        if "ram=" in elem:
            obj["min_ram"] = elem.split("=")[1]
            continue

        if "slot=" in elem:
            obj["slot"] = elem.split("=")[1]
            # Do not set continue because
            # slot is part of Timos Line

        if not skip_nics and "max_nics=" in elem:
            obj["max_nics"] = int(elem.split("=")[1])
            continue
        timos_line.append(elem)
    obj["timos_line"] = " ".join(timos_line)

    # set default cpu and ram
    if "cpu" not in obj:
        obj["cpu"] = 2

    if "min_ram" not in obj:
        obj["min_ram"] = 4

    # set default value for slot
    if "slot" not in obj:
        if "lc:" in cfg:
            obj["slot"] = 1
        else:
            obj["slot"] = "A"

    return obj


def parse_custom_variant(cfg):
    """Parse custom variant definition from a users input returning a variant dict
    an example of user defined variant configuration
    1) integrated:  cpu=2 ram=4 max_nics=6 chassis=sr-1 slot=A card=cpm-1 slot=1 mda/1=me6-100gb-qsfp28
    2) distributed: cp: cpu=2 ram=4 chassis=ixr-e slot=A card=cpm-ixr-e ___
                    lc: cpu=2 ram=4 max_nics=34 chassis=ixr-e slot=1 card=imm24-sfp++8-sfp28+2-qsfp28
                        mda/1=m24-sfp++8-sfp28+2-qsfp28
    """

    # init variant object that gets returned
    variant = {
        "max_nics": 40
    }  # some default value for num nics if it is not provided in user cfg

    # parsing distributed custom variant
    if "___" in cfg:
        variant["deployment_model"] = "distributed"
        variant["lcs"] = []

        for hw_part in cfg.split("___"):
            if "cp: " in hw_part:
                variant["cp"] = parse_variant_line(
                    hw_part.strip(), None, skip_nics=True
                )
            elif "lc: " in hw_part:
                lc = parse_variant_line(hw_part.strip(), None)
                variant["lcs"].append(lc)

        # Sort lc line by slot number
        variant["lcs"] = sort_lc_lines_by_slot(variant["lcs"])
    else:
        # parsing integrated mode config
        variant["deployment_model"] = "integrated"
        variant = parse_variant_line(cfg, obj=variant)

    return variant


# sort line card definitions if they were provided in a non-consequetive order
def sort_lc_lines_by_slot(lc_lines: list) -> list:
    max_slot = 99
    timos_tuples = [(v.get("slot", max_slot), v) for v in lc_lines]
    sorted_timos = [t_tupple[1] for t_tupple in sorted(timos_tuples)]
    return sorted_timos


def mangle_uuid(uuid):
    """Mangle the UUID to fix endianness mismatch on first part"""
    parts = uuid.split("-")

    new_parts = [
        uuid_rev_part(parts[0]),
        uuid_rev_part(parts[1]),
        uuid_rev_part(parts[2]),
        parts[3],
        parts[4],
    ]

    return "-".join(new_parts)


def uuid_rev_part(part):
    """Reverse part of a UUID"""
    res = ""
    for i in reversed(range(0, len(part), 2)):
        res += part[i]
        res += part[i + 1]
    return res


def gen_bof_config():
    """generate bof configuration commands based on env vars and SR OS version"""
    cmds = []
    if "DOCKER_NET_V4_ADDR" in os.environ and os.getenv("DOCKER_NET_V4_ADDR") != "":
        if SROS_VERSION.major >= 23:
            cmds.append(
                f'/bof router static-routes route {os.getenv("DOCKER_NET_V4_ADDR")} next-hop {BRIDGE_V4_ADDR}'
            )
        else:
            cmds.append(
                f'/bof static-route {os.getenv("DOCKER_NET_V4_ADDR")} next-hop {BRIDGE_V4_ADDR}'
            )
    if "DOCKER_NET_V6_ADDR" in os.environ and os.getenv("DOCKER_NET_V6_ADDR") != "":
        if SROS_VERSION.major >= 23:
            cmds.append(
                f'/bof router static-routes route {os.getenv("DOCKER_NET_V6_ADDR")} next-hop {BRIDGE_V6_ADDR}'
            )
        else:
            cmds.append(
                f'/bof static-route {os.getenv("DOCKER_NET_V6_ADDR")} next-hop {BRIDGE_V6_ADDR}'
            )
    # if "docker-net-v6-addr" in m:
    #     cmds.append(f"/bof static-route {m[docker-net-v6-addr]} next-hop {BRIDGE_ADDR}")
    return cmds


class SROS_vm(vrnetlab.VM):
    def __init__(self, username, password, ram, conn_mode, cpu=2, num=0):
        super().__init__(username, password, disk_image="/sros.qcow2", num=num, ram=ram)
        self.nic_type = "virtio-net-pci"
        self.conn_mode = conn_mode
        self.uuid = "00000000-0000-0000-0000-000000000000"
        self.power = "dc"  # vSR emulates DC only
        self.read_license()
        if not cpu or cpu == 0 or cpu == "0":
            cpu = 2
        self.cpu = cpu
        self.qemu_args.extend(["-cpu", "host", "-smp", f"{cpu}"])

        # override default wait pattern with hash followed by the space
        self.wait_pattern = "# "

    # override wait_write clean_buffer parameter default
    def wait_write(self, cmd, wait="__defaultpattern__", con=None, clean_buffer=True):
        super().wait_write( cmd, wait, con, clean_buffer)

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        (ridx, match, res) = self.tn.expect([b"Login:", b"^[^ ]+#"], 1)
        if match:  # got a match!
            if ridx == 0:  # matched login prompt, so should login
                self.logger.debug("matched login prompt")
                self.wait_write("admin", wait=None)
                self.wait_write("admin", wait="Password:")
            # run main config!
            self.bootstrap_config()
            # close telnet connection
            self.tn.close()
            # calc startup time
            startup_time = datetime.datetime.now() - self.start_time
            self.logger.info("Startup complete in: %s" % startup_time)
            self.running = True
            return

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b"":
            self.logger.trace("OUTPUT: %s" % res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return

    def read_license(self):
        """Read the license file, if it exists, and extract the UUID and start
        time of the license
        """
        if not os.path.isfile("/tftpboot/license.txt"):
            self.logger.info("No license file found")
            return

        lic_file = open("/tftpboot/license.txt", "r")
        license = ""
        for line in lic_file.readlines():
            # ignore comments in license file
            if line.startswith("#"):
                continue
            license += line
        lic_file.close()
        try:
            uuid_input = license.split(" ")[0]
            self.uuid = mangle_uuid(uuid_input)
            self.uuid = uuid_input
            m = re.search("([0-9]{4}-[0-9]{2}-)([0-9]{2})", license)
            if m:
                self.fake_start_date = "%s%02d" % (m.group(1), int(m.group(2)) + 1)
        except Exception:
            raise ValueError("Unable to parse license file")
        self.logger.info(
            "License file found for UUID %s with start date %s"
            % (self.uuid, self.fake_start_date)
        )

    # configure power modules
    def configure_power(self, power_cfg):
        """
        Configure power shelf/ves and modules
        """
        shelves = power_cfg["shelves"] if "shelves" in power_cfg else 1
        modules = power_cfg["modules"]
        if type(modules) is dict:
            modules = modules[self.power]  # 3(AC) or 4(DC)

        if self.power == "dc":  # vSIM default
            power_shelf_type = f"ps-a{modules}-shelf-dc"
            module_type = "ps-a-dc-6000"

        # power_path sets the configuration path to access power shelf and module
        # it is different for SR OS version <= 22
        power_path = "chassis router chassis-number 1"
        if SROS_VERSION.major <= 22:
            power_path = "system"

        for s in range(1, shelves + 1):
            self.wait_write(
                f"/configure {power_path} power-shelf {s} power-shelf-type {power_shelf_type}"
            )
            for m in range(1, modules + 1):
                self.wait_write(
                    f"/configure {power_path} power-shelf {s} power-module {m} power-module-type {module_type}"
                )

    def enterConfig(self):
        """Enter configuration mode. No-op for SR OS version <= 22"""
        if SROS_VERSION.major <= 22:
            return
        self.wait_write("edit-config exclusive")

    def enterBofConfig(self):
        """Enter bof configuration mode. No-op for SR OS version <= 22"""
        if SROS_VERSION.major <= 22:
            return
        self.wait_write("edit-config bof exclusive")

    def commitConfig(self):
        """Commit configuration. No-op for SR OS version <= 22"""
        if SROS_VERSION.major <= 22:
            return
        self.wait_write("commit")
        self.wait_write("/")
        self.wait_write("quit-config")

    def commitBofConfig(self):
        """Commit configuration. No-op for SR OS version <= 22"""
        if SROS_VERSION.major <= 22:
            return
        self.wait_write("commit")
        self.wait_write("/")
        self.wait_write("quit-config")

    def configureCards(self):
        """Configure cards"""
        # integrated vsims have `card_config` in the variant definition
        if "card_config" in self.variant:
            for line in iter(self.variant["card_config"].splitlines()):
                self.wait_write(line)
        # else this might be a distributed chassis
        elif self.variant.get("lcs") is not None:
            for lc in self.variant["lcs"]:
                if "card_config" in lc:
                    for line in iter(lc["card_config"].splitlines()):
                        self.wait_write(line)

    def persistBofAndConfig(self):
        """ "Persist bof and config"""
        if SROS_VERSION.major <= 22:
            self.wait_write("/bof save")
            self.wait_write("/admin save")
        else:
            self.wait_write("/admin save bof")
            self.wait_write("/admin save")

    def switchConfigEngine(self):
        """Switch configuration engine"""
        if SROS_VERSION.major <= 22:
            # for SR OS version <= 22, we enforce MD-CLI by switching to it
            self.wait_write(
                f"/configure system management-interface configuration-mode {self.mode}"
            )

    def bootstrap_config(self):
        """Common function used to push initial configuration for bof and config to
        both integrated and distributed nodes."""

        # apply common configuration if config file was not provided
        if not os.path.isfile("/tftpboot/config.txt"):
            self.logger.info("Applying basic SR OS configuration...")

            # enter config mode, no-op for sros <=22
            self.enterConfig()

            for line in iter(
                getDefaultConfig().format(name=self.hostname).splitlines()
            ):
                self.wait_write(line)

            # configure card/mda of a given variant
            self.configureCards()

            # configure power modules
            if "power" in self.variant:
                self.configure_power(self.variant["power"])

            self.commitConfig()

            # configure bof
            self.enterBofConfig()
            for line in iter(gen_bof_config()):
                self.wait_write(line)
            self.commitBofConfig()

            # save bof config on disk
            self.persistBofAndConfig()

            self.switchConfigEngine()

            # logout at the end of execution
            self.wait_write("/logout")


class SROS_integrated(SROS_vm):
    """Integrated VSR-SIM"""

    def __init__(
        self, hostname, username, password, mode, num_nics, variant, conn_mode
    ):
        ram: int = vrnetlab.getMem("integrated", variant.get("min_ram"))
        cpu: int = vrnetlab.getCpu("integrated", variant.get("cpu"))

        super().__init__(
            username,
            password,
            cpu=cpu,
            ram=ram,
            conn_mode=conn_mode,
        )
        self.mode = mode
        self.role = "integrated"
        self.num_nics = num_nics
        self.smbios = [
            f"type=1,product=TIMOS:address={SROS_MGMT_V4_ADDR}/{V4_PREFIX_LENGTH}@active "
            f"address={SROS_MGMT_V6_ADDR}/{V6_PREFIX_LENGTH}@active license-file=tftp://{BRIDGE_V4_ADDR}/"
            f"license.txt primary-config=tftp://{BRIDGE_V4_ADDR}/config.txt system-base-mac={vrnetlab.gen_mac(0)} "
            f"{variant['timos_line']}"
        ]
        self.logger.info("Acting timos line: {}".format(self.smbios))
        self.variant = variant
        self.hostname = hostname

    def gen_mgmt(self):
        """
        Generate SR OS MGMT interface connected to a mgmt bridge
        """

        res = []

        res.append("-device")

        res.append(
            self.nic_type + ",netdev=br-mgmt,mac=%(mac)s" % {"mac": vrnetlab.gen_mac(0)}
        )
        res.append("-netdev")
        res.append("bridge,br=br-mgmt,id=br-mgmt" % {"i": 0})

        if (
            "chassis=ixr-r6" in self.variant["timos_line"]
            or "chassis=ixr-ec" in self.variant["timos_line"]
        ):
            logger.debug(
                "detected ixr-r6/ec chassis, creating a dummy network device for SFM connection"
            )
            res.append(f"-device virtio-net-pci,netdev=dummy,mac={vrnetlab.gen_mac(0)}")
            res.append("-netdev tap,ifname=sfm-dummy,id=dummy,script=no,downscript=no")

        return res


class SROS_cp(SROS_vm):
    """Control plane for distributed VSR-SIM"""

    def __init__(self, hostname, username, password, mode, variant, conn_mode):
        # cp - control plane. role is used to create a separate overlay image name
        self.role = "cp"

        ram: int = vrnetlab.getMem(self.role, variant.get("cp").get("min_ram"))
        cpu: int = vrnetlab.getCpu(self.role, variant.get("cp").get("cpu"))

        super(SROS_cp, self).__init__(
            username,
            password,
            cpu=cpu,
            ram=ram,
            conn_mode=conn_mode,
        )
        self.mode = mode
        self.num_nics = 0
        self.hostname = hostname
        self.variant = variant

        self.smbios = [
            f"type=1,product=TIMOS:address={SROS_MGMT_V4_ADDR}/{V4_PREFIX_LENGTH}@active "
            f"address={SROS_MGMT_V6_ADDR}/{V6_PREFIX_LENGTH}@active "
            f"license-file=tftp://{BRIDGE_V4_ADDR}/license.txt "
            f"primary-config=tftp://{BRIDGE_V4_ADDR}/config.txt "
            f"system-base-mac={vrnetlab.gen_mac(0)} {variant['cp']['timos_line']}"
        ]
        self.logger.info("Acting timos line: {}".format(self.smbios))

    def start(self):
        # use parent class start() function
        super(SROS_cp, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(["brctl", "addif", "int_cp", "vcp-int"])
        vrnetlab.run_command(["ip", "link", "set", "vcp-int", "up"])
        vrnetlab.run_command(["ip", "link", "set", "dev", "vcp-int", "mtu", "10000"])

    def gen_nics(self):
        """
        Override the parent's gen_nic function,
        since dataplane interfaces are not to be created for CPM
        """
        return []

    def gen_mgmt(self):
        """
        Generate mgmt interface(s)
        """
        res = []

        res.append("-device")

        res.append(
            self.nic_type + ",netdev=br-mgmt,mac=%(mac)s" % {"mac": vrnetlab.gen_mac(0)}
        )
        res.append("-netdev")
        res.append("bridge,br=br-mgmt,id=br-mgmt" % {"i": 0})

        # add virtio NIC for internal control plane interface to vFPC
        res.append("-device")
        res.append("virtio-net-pci,netdev=vcp-int,mac=%s" % vrnetlab.gen_mac(1))
        res.append("-netdev")
        res.append("tap,ifname=vcp-int,id=vcp-int,script=no,downscript=no")
        return res


class SROS_lc(SROS_vm):
    """Line card for distributed VSR-SIM"""

    def __init__(self, lc_config, conn_mode, num_nics, slot=1, nic_eth_start=1):
        # role lc if for a line card. role is used to create a separate overlay image name
        self.role = "lc"

        ram: int = vrnetlab.getMem(self.role, lc_config.get("min_ram"))
        cpu: int = vrnetlab.getCpu(self.role, lc_config.get("cpu"))

        super(SROS_lc, self).__init__(
            None,
            None,
            ram=ram,
            conn_mode=conn_mode,
            num=slot,
            cpu=cpu,
        )

        self.smbios = ["type=1,product=TIMOS:{}".format(lc_config["timos_line"])]
        self.slot = slot
        self.num_nics = num_nics
        self.start_nic_eth_idx = nic_eth_start

    def start(self):
        # use parent class start() function
        super(SROS_lc, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(
            ["brctl", "addif", "int_cp", "vfpc{}-int".format(self.slot)]
        )
        vrnetlab.run_command(
            ["ip", "link", "set", "vfpc{}-int".format(self.slot), "up"]
        )
        vrnetlab.run_command(
            ["ip", "link", "set", "dev", "vfpc{}-int".format(self.slot), "mtu", "10000"]
        )

    def gen_mgmt(self):
        """Generate mgmt interface"""
        res = []
        # mgmt interface, dummy on line card VMs just to get correct PCI id order
        res.extend(
            ["-device", "virtio-net-pci,netdev=mgmt,mac=%s" % vrnetlab.gen_mac(0)]
        )
        res.extend(["-netdev", "user,id=mgmt,restrict=y"]) # dummy nic, not used
        # internal control plane interface to vFPC
        res.extend(
            ["-device", "virtio-net-pci,netdev=vfpc-int,mac=%s" % vrnetlab.gen_mac(0)]
        )
        res.extend(
            [
                "-netdev",
                "tap,ifname=vfpc{}-int,id=vfpc-int,script=no,downscript=no".format(
                    self.slot
                ),
            ]
        )
        return res

    def bootstrap_spin(self):
        """We have nothing to do for VSR-SIM line cards"""
        self.running = True
        self.tn.close()
        return


# SROS is main class for VSR-SIM
class SROS(vrnetlab.VR):
    def __init__(self, hostname, username, password, mode, variant_name, conn_mode):
        super().__init__(username, password)

        if variant_name.lower() in SROS_VARIANTS:
            variant = SROS_VARIANTS[variant_name.lower()]

            if variant.get("lcs", None):
                variant["lcs"] = [
                    parse_variant_line(lc.get("timos_line", ""), lc)
                    for lc in variant["lcs"]
                ]
        else:
            variant = parse_custom_variant(variant_name)

        self.extractVersion()
        self.processFiles()

        self.license = False
        if os.path.isfile("/tftpboot/license.txt"):
            self.logger.info("License found")
            self.license = True
        else:
            self.logger.error(
                "License is missing! Provide a license file with a {}.license name next to the qcow2 image.".format(
                    self.qcow_name
                )
            )
            sys.exit(1)

        self.logger.debug("Raw SR OS variant: " + str(variant))
        self.logger.info("SR OS Variant: " + variant_name)
        self.logger.info(f"Number of NICs: {variant['max_nics']}")
        self.logger.info("Configuration mode: " + str(mode))

        self.setupMgmtBridge()

        if variant["deployment_model"] == "distributed":
            # CP VM instantiation
            self.vms = [
                SROS_cp(
                    hostname,
                    username,
                    password,
                    mode,
                    variant,
                    conn_mode,
                )
            ]

            # LC VM Instantiation
            start_eth = 1
            lc_slot_tracker = []
            for lc in variant["lcs"]:
                lc_slot = lc.get("slot", None)

                # If lc_slot does not exist the skip instantiation
                if not lc_slot:
                    self.logger.warning(
                        f"No Slot information on following lc line defintion: {lc}"
                        "Skip LC VM creation"
                    )
                    continue

                if lc_slot in lc_slot_tracker:
                    self.logger.warning(
                        f"Found duplicate slot: {lc} Skip LC VM creation"
                    )
                    continue

                try:
                    lc_slot = int(lc_slot)
                except (TypeError, ValueError):
                    self.logger.warning(
                        f"slot value format is not valid: {lc} Skip LC VM creation"
                    )
                    continue

                # Priority is to use max_nics from each lc definition
                max_nics = lc.get("max_nics", None)
                if not max_nics:
                    max_nics = variant["max_nics"]

                self.vms.append(
                    SROS_lc(
                        lc,
                        conn_mode,
                        max_nics,
                        slot=lc_slot,
                        nic_eth_start=start_eth,
                    )
                )

                # Ethernet sequence is based on attached linecard respecting slot sequence
                start_eth += int(max_nics)
                lc_slot_tracker.append(lc_slot)

            # set up bridge for connecting CP with LCs
            vrnetlab.run_command(["brctl", "addbr", "int_cp"])
            vrnetlab.run_command(["ip", "link", "set", "int_cp", "up"])
        # integrated mode
        else:
            self.vms = [
                SROS_integrated(
                    hostname,
                    username,
                    password,
                    mode,
                    variant["max_nics"],
                    variant,
                    conn_mode=conn_mode,
                )
            ]

    def setupMgmtBridge(self):
        # set up bridge for management interface to a localhost
        self.logger.info("Creating br-mgmt bridge for management interface")
        # This is to whitlist all bridges
        vrnetlab.run_command(["mkdir", "-p", "/etc/qemu"])
        vrnetlab.run_command(["echo 'allow all' > /etc/qemu/bridge.conf"], shell=True)
        # Enable IPv6 inside the container
        vrnetlab.run_command(["sysctl net.ipv6.conf.all.disable_ipv6=0"], shell=True)
        # Enable IPv6 routing inside the container
        vrnetlab.run_command(["sysctl net.ipv6.conf.all.forwarding=1"], shell=True)
        vrnetlab.run_command(["brctl", "addbr", "br-mgmt"])
        vrnetlab.run_command(
            ["echo 16384 > /sys/class/net/br-mgmt/bridge/group_fwd_mask"],
            shell=True,
        )
        vrnetlab.run_command(["ip", "link", "set", "br-mgmt", "up"])
        vrnetlab.run_command(
            [
                "ip",
                "addr",
                "add",
                "dev",
                "br-mgmt",
                f"{BRIDGE_V4_ADDR}/{V4_PREFIX_LENGTH}",
            ]
        )
        vrnetlab.run_command(
            [
                "ip",
                "addr",
                "add",
                "dev",
                "br-mgmt",
                f"{BRIDGE_V6_ADDR}/{V6_PREFIX_LENGTH}",
            ]
        )

    def extractVersion(self):
        """extractVersion extracts the SR OS version from the qcow2 image name"""
        # https://regex101.com/r/SPefOu/1
        pattern = r"\S+-((\d{1,3})\.(\d{1,2})\.\w(\d{1,2}))\.qcow2"
        match_found = False

        for e in os.listdir("/"):
            match = re.match(pattern, e)
            if match:
                # save original qcow2 image name
                self.qcow_name = e

                SROS_VERSION.version = str(match.group(1))
                SROS_VERSION.major = int(match.group(2))
                SROS_VERSION.minor = int(match.group(3))
                SROS_VERSION.patch = int(match.group(4))
                self.logger.info(f"Parsed SR OS version: {SROS_VERSION}")

                match_found = True
                break

        if not match_found:
            self.logger.error("Could not extract version from qcow2 image name")

    def processFiles(self):
        """processFiles renames the qcow2 image to sros.qcow2 and the license file to license.txt
        as well as returning the major release number extracted from the qcow2 image name
        """
        os.rename("/" + self.qcow_name, "/sros.qcow2")
        for e in os.listdir("/"):
            if re.search(r"\.license$", e):
                shutil.move("/" + e, "/tftpboot/license.txt")


def getDefaultConfig() -> str:
    """Returns the default configuration for the system based on the SR OS version.
    SR OS >=23 uses model-driven configuration, while SR OS <=22 uses classic configuration.
    """

    if SROS_VERSION.major <= 22:
        return SROS_CL_COMMON_CFG

    return SROS_MD_COMMON_CFG


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--hostname", default="vr-sros", help="Router hostname")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
    parser.add_argument(
        "--mode",
        choices=["classic", "mixed", "model-driven"],
        default="model-driven",
        help="configuration mode of the system",
    )
    parser.add_argument(
        "--variant",
        default="sr-1",
        help="Variant of SR OS platform to launch",
    )
    parser.add_argument(
        "--connection-mode",
        default="vrxcon",
        help="Connection mode to use in the datapath",
    )
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vrnetlab.run_command(
        [
            "in.tftpd",
            "--listen",
            "--user",
            "tftp",
            "-a",
            "0.0.0.0:69",
            "-s",
            "-c",
            "-v",
            "-p",
            "/tftpboot",
        ]
    )

    # make tftpboot writable for saving SR OS config
    vrnetlab.run_command(["chmod", "-R", "777", "/tftpboot"])

    # kill origin socats since we use bridge interface
    # for SR OS management interface
    # thus we need to forward connections to a different address
    vrnetlab.run_command(["pkill", "socat"])

    # redirecting incoming tcp traffic (except serial port 5000) from eth0 to SR management interface
    vrnetlab.run_command(
        f"iptables-nft -t nat -A PREROUTING -i eth0 -p tcp ! --dport 5000 -j DNAT --to-destination {SROS_MGMT_V4_ADDR}".split()
    )
    vrnetlab.run_command(
        f"ip6tables-nft -t nat -A PREROUTING -i eth0 -p tcp ! --dport 5000 -j DNAT --to-destination {SROS_MGMT_V6_ADDR}".split()
    )
    # same redirection but for UDP
    vrnetlab.run_command(
        f"iptables-nft -t nat -A PREROUTING -i eth0 -p udp -j DNAT --to-destination {SROS_MGMT_V4_ADDR}".split()
    )
    vrnetlab.run_command(
        f"ip6tables-nft -t nat -A PREROUTING -i eth0 -p udp -j DNAT --to-destination {SROS_MGMT_V6_ADDR}".split()
    )
    # masquerading the incoming traffic so SR OS is able to reply back
    vrnetlab.run_command(
        "iptables-nft -t nat -A POSTROUTING -o br-mgmt -j MASQUERADE".split()
    )
    vrnetlab.run_command(
        "ip6tables-nft -t nat -A POSTROUTING -o br-mgmt -j MASQUERADE".split()
    )
    # allow sros breakout to management network by NATing via eth0
    vrnetlab.run_command(
        "iptables-nft -t nat -A POSTROUTING -o eth0 -j MASQUERADE".split()
    )
    vrnetlab.run_command(
        "ip6tables-nft -t nat -A POSTROUTING -o eth0 -j MASQUERADE".split()
    )

    logger.debug(
        f"acting flags: username '{args.username}', password '{args.password}', connection-mode '{args.connection_mode}', variant '{args.variant}'"
    )

    logger.debug(f"Environment variables: {os.environ}")

    vrnetlab.boot_delay()

    ia = SROS(
        args.hostname,
        args.username,
        args.password,
        mode=args.mode,
        variant_name=args.variant,
        conn_mode=args.connection_mode,
    )
    ia.start(add_fwd_rules=False)
