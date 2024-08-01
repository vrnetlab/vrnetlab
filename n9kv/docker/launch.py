#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import sys
import time

import vrnetlab

STARTUP_CONFIG_FILE = "/config/startup-config.cfg"


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


class N9KV_vm(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode):
        disk_image = ""
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        if disk_image == "":
            logging.getLogger().info("Disk image was not found")
            exit(1)
        super(N9KV_vm, self).__init__(
            username, password, disk_image=disk_image, ram=8192, cpu="host,level=9"
        )
        self.hostname = hostname
        self.conn_mode = conn_mode
        # mgmt + 128 that show up in the vm, may as well populate them all in vrnetlab right away
        self.num_nics = 129
        self.nic_type = "e1000"

        # bios for n9kv
        self.qemu_args.extend(["-bios", "/OVMF.fd"])

        overlay_disk_image = re.sub(r"(\.[^.]+$)", r"-overlay\1", disk_image)
        # boot harddrive first
        self.qemu_args.extend(["-boot", "c"])
        replace_index = self.qemu_args.index(
            "if=ide,file={}".format(overlay_disk_image)
        )
        self.qemu_args[
            replace_index
        ] = "file={},if=none,id=drive-sata-disk0,format=qcow2".format(
            overlay_disk_image
        )
        self.qemu_args.extend(["-device", "ahci,id=ahci0,bus=pci.0"])
        self.qemu_args.extend(
            [
                "-device",
                "ide-hd,drive=drive-sata-disk0,bus=ahci0.0,id=drive-sata-disk0,bootindex=1",
            ]
        )


    def bootstrap_spin(self):
        """This function should be called periodically to do work."""
        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"\(yes\/skip\/no\)\[no\]:",b"\(yes\/no\)\[n\]:", b"login:"], 1)
        if match:  # got a match!
            if ridx == 0 or ridx == 1:
                self.logger.debug("matched poap prompt")
                self.wait_write("yes", wait=None)
                self.wait_write(
                    "no", wait="Do you want to enforce secure password standard"
                )
                self.wait_write(self.password, wait='Enter the password for "admin"')
                self.wait_write(self.password, wait='Confirm the password for "admin"')
                self.wait_write(
                    "no", wait="Would you like to enter the basic configuration dialog"
                )
            elif ridx == 2:  # login
                self.logger.debug("matched login prompt")
                self.logger.debug(f'trying to log in with "admin" / {self.password}')
                self.wait_write("admin", wait=None)
                self.wait_write(self.password, wait="Password:")

                # run main config!
                self.bootstrap_config()
                self.startup_config()
                # close telnet connection
                self.tn.close()
                # startup time?
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s" % startup_time)
                # mark as running
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

    def bootstrap_config(self):
        """Do the actual bootstrap config"""
        self.logger.info("applying bootstrap configuration")
        self.wait_write("", None)
        self.wait_write("configure")
        self.wait_write(f"hostname {self.hostname}")
        self.wait_write(
            f"username {self.username} password 0 {self.password} role network-admin"
        )
        
        # configure management vrf
        self.wait_write("vrf context management")
        self.wait_write("ip route 0.0.0.0/0 10.0.0.2")
        self.wait_write("exit")

        # configure mgmt interface
        self.wait_write("interface mgmt0")
        self.wait_write("ip address 10.0.0.15/24")
        self.wait_write("exit")

        # setup nxapi/scp server
        self.wait_write("feature scp-server")
        self.wait_write("feature nxapi")
        self.wait_write("feature telnet")
        self.wait_write("feature netconf")
        self.wait_write("feature grpc")
        self.wait_write("exit")
        self.wait_write("copy running-config startup-config")
        self.wait_write("! Bootstrap Config for ContainerLab Complete.", wait="Copy complete.")

    def startup_config(self):
        """Load additional config provided by user."""

        if not os.path.exists(STARTUP_CONFIG_FILE):
            self.logger.trace(f"Startup config file {STARTUP_CONFIG_FILE} is not found")
            return

        self.logger.trace(f"Startup config file {STARTUP_CONFIG_FILE} exists")
        with open(STARTUP_CONFIG_FILE) as file:
            config_lines = file.readlines()
            config_lines = [line.rstrip() for line in config_lines]
            self.logger.trace(f"Parsed startup config file {STARTUP_CONFIG_FILE}")

        self.logger.info(f"Writing lines from {STARTUP_CONFIG_FILE}")

        self.wait_write("configure terminal")
        # Apply lines from file
        for line in config_lines:
            self.wait_write(line)
        # End and Save
        self.wait_write("end")
        self.wait_write("copy running-config startup-config")


class N9KV(vrnetlab.VR):
    def __init__(self, hostname, username, password, conn_mode):
        super(N9KV, self).__init__(username, password)
        self.vms = [N9KV_vm(hostname, username, password, conn_mode)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--hostname", default="vr-n9kv", help="Router hostname")
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
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

    logger.debug(f"Environment variables: {os.environ}")
    vrnetlab.boot_delay()

    vr = N9KV(args.hostname, args.username, args.password, args.connection_mode)
    vr.start()
