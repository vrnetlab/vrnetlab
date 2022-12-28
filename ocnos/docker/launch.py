#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import sys

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


class OCNOS_vm(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode):
        disk_image = ""
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        if disk_image == "":
            logging.getLogger().info("Disk image was not found")
            exit(1)
        super(OCNOS_vm, self).__init__(
            username, password, disk_image=disk_image, ram=4096
        )
        self.hostname = hostname
        self.conn_mode = conn_mode
        self.num_nics = 8
        self.nic_type = "virtio-net-pci"

        self.qemu_args.extend(["-cpu", "host,level=9"])
        self.qemu_args.extend(["-smp", "2,sockets=1,cores=1"])

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.logger.info("To many spins with no result, restarting")
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"OcNOS login:"], 1)
        if match:  # got a match!
            if ridx == 0:  # login
                self.logger.debug("matched login prompt")
                self.logger.debug("trying to log in with 'ocnos'")
                self.wait_write("ocnos", wait=None)
                self.wait_write("ocnos", wait="Password:")

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
        self.wait_write("enable", ">")
        self.wait_write("configure terminal")
        self.wait_write(
            "username %s role network-admin password %s"
            % (self.username, self.password)
        )

        # configure mgmt interface
        self.wait_write("interface eth0")
        self.wait_write("ip address 10.0.0.15 255.255.255.0")
        self.wait_write("exit")

        self.wait_write(f"hostname {self.hostname}")

        self.wait_write("commit")
        self.wait_write("exit")
        self.wait_write("write memory")

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
        self.wait_write("commit")
        self.wait_write("end")
        self.wait_write("write memory")

    def gen_mgmt(self):
        """
        Augment base gen_mgmt function to add gnmi and socat forwarding
        """
        res = []

        res.append("-device")
        res.append(self.nic_type + f",netdev=mgmt,mac={vrnetlab.gen_mac(0)}")

        res.append("-netdev")
        res.append(
            "user,id=mgmt,net=10.0.0.0/24,tftp=/tftpboot,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=tcp::2023-10.0.0.15:23,hostfwd=udp::2161-10.0.0.15:161,hostfwd=tcp::2443-10.0.0.15:443,hostfwd=tcp::2830-10.0.0.15:830"
        )
        return res


class OCNOS(vrnetlab.VR):
    def __init__(self, hostname, username, password, conn_mode):
        super(OCNOS, self).__init__(username, password)
        self.vms = [OCNOS_vm(hostname, username, password, conn_mode)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--hostname", default="vr-xrv9k", help="Router hostname")
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

    vr = OCNOS(args.hostname, args.username, args.password, args.connection_mode)
    vr.start()
