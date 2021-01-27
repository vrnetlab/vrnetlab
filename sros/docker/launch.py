#!/usr/bin/env python3

import datetime
import logging
import math
import os
import re
import signal
import sys
import time
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

SROS_VARIANTS = {
    "sr-1": {
        "deployment_model": "integrated",
        "min_ram": 5120,  # minimum RAM requirements
        "max_nics": 6,
        "timos_line": "chassis=sr-1 slot=A card=cpm-1 slot=1 mda/1=me6-100gb-qsfp28",
        "card_config": """/configure card 1 card-type iom-1
        /configure card 1 mda 1 mda-type me6-100gb-qsfp28
        """,
    },
    "sr-1e": {
        "deployment_model": "distributed",
        # control plane (CPM)
        "max_nics": 20,
        "cp": {
            "min_ram": 4096,
            "timos_line": "slot=A chassis=sr-1e card=cpm-e",
        },
        # line card (IOM/XCM)
        "lc": {
            "min_ram": 4096,
            "timos_line": "chassis=sr-1e slot=1 card=iom-e mda/1=me40-1gb-csfp",
            "card_config": """/configure card 1 card-type iom-e
            /configure card 1 mda 1 mda-type me40-1gb-csfp
            /configure card 1 fp 1
            """,
        },
    },
}

SROS_COMMON_CFG = """/configure system name {name}
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

# to allow writing config to tftp location we needed to spin up a normal
# tftp server in container host system. To access the host from qemu VM
# we needed to put SR OS management interface in the container host network namespace
# this is done by putting SR OS management interface with into a br-mgmt bridge
# the bridge and SR OS mgmt interfaces will be addressed as follows
BRIDGE_ADDR = "172.31.255.29"
SROS_MGMT_ADDR = "172.31.255.30"
PREFIX_LENGTH = "30"


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


class SROS_vm(vrnetlab.VM):
    def __init__(self, username, password, ram, conn_mode, num=0):
        super(SROS_vm, self).__init__(
            username, password, disk_image="/sros.qcow2", num=num, ram=ram
        )
        self.conn_mode = conn_mode
        self.uuid = "00000000-0000-0000-0000-000000000000"
        self.read_license()

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 60:
            # too many spins with no result, probably means SROS hasn't started
            # successfully, so we restart it
            self.logger.warning("no output from serial console, restarting VM")
            self.stop()
            self.start()
            self.spins = 0
            return

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
        except:
            raise ValueError("Unable to parse license file")
        self.logger.info(
            "License file found for UUID %s with start date %s"
            % (self.uuid, self.fake_start_date)
        )


class SROS_integrated(SROS_vm):
    """Integrated VSR-SIM"""

    def __init__(
        self, hostname, username, password, mode, num_nics, variant, conn_mode
    ):
        super(SROS_integrated, self).__init__(
            username, password, ram=variant["min_ram"], conn_mode=conn_mode
        )
        self.mode = mode
        self.num_nics = num_nics
        self.smbios = [
            f"type=1,product=TIMOS:address={SROS_MGMT_ADDR}/{PREFIX_LENGTH}@active license-file=tftp://{BRIDGE_ADDR}/license.txt primary-config=tftp://{BRIDGE_ADDR}/config.txt {variant['timos_line']}"
        ]
        self.logger.info("Acting timos line: {}".format(self.smbios))
        self.variant = variant
        self.hostname = hostname

    def gen_mgmt(self):
        """Generate mgmt interface(s)

        We override the default function since we want a fake NIC in there
        """

        """Generate qemu args for the mgmt interface(s)"""
        res = []

        res.append("-device")

        res.append(
            self.nic_type + ",netdev=br-mgmt,mac=%(mac)s" % {"mac": vrnetlab.gen_mac(0)}
        )
        res.append("-netdev")
        res.append("bridge,br=br-mgmt,id=br-mgmt" % {"i": 0})

        return res

    def bootstrap_config(self):
        """Do the actual bootstrap config"""

        # apply common configuration if config file was not provided
        if not os.path.isfile("/tftpboot/config.txt"):
            self.logger.info("Applying basic SR OS configuration...")
            for l in iter(SROS_COMMON_CFG.format(name=self.hostname).splitlines()):
                self.wait_write(l)

            if self.username and self.password:
                self.wait_write(
                    '/configure system security user "%s" password %s'
                    % (self.username, self.password)
                )
                self.wait_write(
                    '/configure system security user "%s" access console netconf'
                    % (self.username)
                )
                self.wait_write(
                    '/configure system security user "%s" console member "administrative" "default"'
                    % (self.username)
                )

            # configure card/mda of a given variant
            for l in iter(self.variant["card_config"].splitlines()):
                self.wait_write(l)

            self.wait_write("/admin save")
            self.wait_write(
                "/configure system management-interface configuration-mode {mode}".format(
                    mode=self.mode
                )
            )
            self.wait_write("/logout")


class SROS_cp(SROS_vm):
    """Control plane for distributed VSR-SIM"""

    def __init__(
        self, hostname, username, password, mode, major_release, variant, conn_mode
    ):
        # cp - control plane. role is used to create a separate overlay image name
        self.role = "cp"
        super(SROS_cp, self).__init__(
            username, password, variant["cp"]["min_ram"], conn_mode
        )
        self.mode = mode
        self.num_nics = 0
        self.hostname = hostname
        self.variant = variant

        self.smbios = [
            f"type=1,product=TIMOS:address={SROS_MGMT_ADDR}/{PREFIX_LENGTH}@active license-file=tftp://{BRIDGE_ADDR}/license.txt primary-config=tftp://{BRIDGE_ADDR}/config.txt {variant['cp']['timos_line']}"
        ]

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
        """Generate mgmt interface(s)

        We override the default function since we want a NIC to the vFPC
        """
        # call parent function to generate first mgmt interface (e1000)
        res = super(SROS_cp, self).gen_mgmt()
        # add virtio NIC for internal control plane interface to vFPC
        res.append("-device")
        res.append("e1000,netdev=vcp-int,mac=%s" % vrnetlab.gen_mac(1))
        res.append("-netdev")
        res.append("tap,ifname=vcp-int,id=vcp-int,script=no,downscript=no")
        return res

    def bootstrap_config(self):
        """Do the actual bootstrap config"""
        # apply common configuration if config file was not provided
        if not os.path.isfile("/tftpboot/config.txt"):
            for l in iter(SROS_COMMON_CFG.format(name=self.hostname).splitlines()):
                self.wait_write(l)

            if self.username and self.password:
                self.wait_write(
                    '/configure system security user "%s" password %s'
                    % (self.username, self.password)
                )
                self.wait_write(
                    '/configure system security user "%s" access console netconf'
                    % (self.username)
                )
                self.wait_write(
                    '/configure system security user "%s" console member "administrative" "default"'
                    % (self.username)
                )

            # configure card/mda of a given variant
            for l in iter(self.variant["lc"]["card_config"].splitlines()):
                self.wait_write(l)

            self.wait_write("/admin save")
            self.wait_write(
                "/configure system management-interface configuration-mode {mode}".format(
                    mode=self.mode
                )
            )
            self.wait_write("/logout")


class SROS_lc(SROS_vm):
    """Line card for distributed VSR-SIM"""

    def __init__(self, variant, conn_mode, num_nics, slot=1):
        # cp - control plane. role is used to create a separate overlay image name
        self.role = "lc"
        super(SROS_lc, self).__init__(
            None, None, variant["lc"]["min_ram"], conn_mode, num=slot
        )

        self.smbios = ["type=1,product=TIMOS:{}".format(variant["lc"]["timos_line"])]
        self.slot = slot
        self.num_nics = num_nics

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
        # mgmt interface
        res.extend(["-device", "e1000,netdev=mgmt,mac=%s" % vrnetlab.gen_mac(0)])
        res.extend(["-netdev", "user,id=mgmt,net=10.0.0.0/24"])
        # internal control plane interface to vFPC
        res.extend(["-device", "e1000,netdev=vfpc-int,mac=%s" % vrnetlab.gen_mac(0)])
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


class SROS(vrnetlab.VR):
    def __init__(
        self, hostname, username, password, num_nics, mode, variant_name, conn_mode
    ):
        super(SROS, self).__init__(username, password)

        variant = SROS_VARIANTS[variant_name]

        major_release = 0

        # move files into place
        for e in os.listdir("/"):
            match = re.match(r"[^0-9]+([0-9]+)\S+\.qcow2$", e)
            if match:
                major_release = int(match.group(1))
                self.qcow_name = match.group(0)
            if re.search("\.qcow2$", e):
                os.rename("/" + e, "/sros.qcow2")
            if re.search("\.license$", e):
                os.rename("/" + e, "/tftpboot/license.txt")

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

        if num_nics > variant["max_nics"]:
            self.logger.error(
                "Requested number of nics '{}' exceeds the capacity of the '{}' variant: {} nics".format(
                    num_nics, variant_name, variant["max_nics"]
                )
            )
            sys.exit(1)

        self.logger.info("SR OS Variant: " + variant_name)
        self.logger.info("Number of NICs: " + str(num_nics))
        self.logger.info("Configuration mode: " + str(mode))

        # set up bridge for management interface to a localhost
        self.logger.info("Creating br-mgmt bridge for management interface")
        vrnetlab.run_command(["brctl", "addbr", "br-mgmt"])
        vrnetlab.run_command(["ip", "link", "set", "br-mgmt", "up"])
        vrnetlab.run_command(
            ["ip", "addr", "add", "dev", "br-mgmt", f"{BRIDGE_ADDR}/{PREFIX_LENGTH}"]
        )

        if variant["deployment_model"] == "distributed":
            self.vms = [
                SROS_cp(
                    hostname,
                    username,
                    password,
                    mode,
                    major_release,
                    variant,
                    conn_mode,
                ),
                SROS_lc(variant, conn_mode, num_nics),
            ]

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
                    num_nics,
                    variant,
                    conn_mode=conn_mode,
                )
            ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--hostname", default="vr-sros", help="Router hostname")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
    parser.add_argument("--num-nics", default=5, help="Number of NICs")
    parser.add_argument(
        "--mode",
        choices=["classic", "mixed", "model-driven"],
        default="model-driven",
        help="configuration mode of the system",
    )
    parser.add_argument(
        "--variant",
        choices=["sr-1", "sr-1e"],
        default="sr-1",
        help="Variant of SR OS platform to launch",
    )
    parser.add_argument(
        "--connection-mode",
        choices=["vrxcon", "macvtap", "bridge"],
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

    # vrnetlab.run_command(["apt", "update"])
    # vrnetlab.run_command(["apt", "install", "-y", "tftpd-hpa"])
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
            "/tftpboot",
        ]
    )

    # make tftpboot writable for saving SR OS config
    vrnetlab.run_command(["chmod", "-R", "777", "/tftpboot"])

    # kill origin socats since we use bridge interface
    # for SR OS management interface
    # thus we need to forward connections to a different address
    vrnetlab.run_command(["pkill", "socat"])
    time.sleep(5)

    # forwarding rules
    vrnetlab.run_command(
        ["socat", "TCP-LISTEN:22,fork", f"TCP:{SROS_MGMT_ADDR}:22"], background=True
    )
    vrnetlab.run_command(
        ["socat", "UDP-LISTEN:161,fork", f"UDP:{SROS_MGMT_ADDR}:161"], background=True
    )
    vrnetlab.run_command(
        ["socat", "TCP-LISTEN:830,fork", f"TCP:{SROS_MGMT_ADDR}:830"], background=True
    )
    vrnetlab.run_command(
        ["socat", "TCP-LISTEN:80,fork", f"TCP:{SROS_MGMT_ADDR}:80"], background=True
    )
    vrnetlab.run_command(
        ["socat", "TCP-LISTEN:443,fork", f"TCP:{SROS_MGMT_ADDR}:443"], background=True
    )
    vrnetlab.run_command(
        ["socat", "TCP-LISTEN:57400,fork", f"TCP:{SROS_MGMT_ADDR}:57400"],
        background=True,
    )

    ia = SROS(
        args.hostname,
        args.username,
        args.password,
        num_nics=int(args.num_nics),
        mode=args.mode,
        variant_name=args.variant,
        conn_mode=args.connection_mode,
    )
    ia.start()
