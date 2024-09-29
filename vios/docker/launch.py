#!/usr/bin/env python3
import datetime
import logging
import os
import re
import signal
import sys

import vrnetlab

STARTUP_CONFIG_FILE = "/config/startup-config.cfg"


def handle_SIGCHLD(_signal, _frame):
    os.waitpid(-1, os.WNOHANG)


def handle_SIGTERM(_signal, _frame):
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


class VIOS_vm(vrnetlab.VM):
    def __init__(self, hostname: str, username: str, password: str, conn_mode: str):
        disk_image = None
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        if not disk_image:
            raise Exception("No disk image found")

        super(VIOS_vm, self).__init__(
            username=username,
            password=password,
            disk_image=disk_image,
            smp="1",
            ram=512,
            driveif="virtio",
        )

        self.hostname = hostname
        self.conn_mode = conn_mode
        # device supports up to 16 interfaces (1 management interface + 15 data interfaces)
        self.num_nics = 15
        self.running = False
        self.spins = 0

    def bootstrap_spin(self):
        if self.spins > 300:
            # too many spins with no result -> give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect(
            [
                rb"Would you like to enter the initial configuration dialog\? \[yes/no\]:",
                b"Press RETURN to get started!",
                b"Router>",
            ],
            1,
        )

        if match:
            if ridx == 0:
                self.logger.info("Skipping initial configuration dialog")
                self.wait_write("no", wait=None)
            elif ridx == 1:
                self.logger.info("Entering user EXEC mode")
                for _ in range(3):
                    self.wait_write("\r", wait=None)
            elif ridx == 2:
                self._enter_config_mode()
                self._bootstrap_config()
                self._load_startup_config()
                self._save_config()

                # close telnet connection
                self.tn.close()
                # startup time
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info(f"Startup complete in: {startup_time}")
                # mark as running
                self.running = True

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b"":
            self.logger.trace(f"OUTPUT: {res.decode()}")
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1
        return

    def _enter_config_mode(self):
        self.logger.info("Entering configuration mode")

        self.wait_write("enable", wait=None)
        self.wait_write("configure terminal")

    def _bootstrap_config(self):
        self.logger.info("Applying initial configuration")

        self.wait_write(f"hostname {self.hostname}")
        self.wait_write(f"ip domain-name {self.hostname}.clab")
        self.wait_write("no ip domain-lookup")

        self.wait_write(f"username {self.username} privilege 15 secret {self.password}")

        self.wait_write("line con 0")
        self.wait_write("logging synchronous")
        self.wait_write("exec-timeout 0 0")
        self.wait_write("login local")
        self.wait_write("exit")

        self.wait_write("line vty 0 4")
        self.wait_write("logging synchronous")
        self.wait_write("exec-timeout 0 0")
        self.wait_write("transport input ssh")
        self.wait_write("login local")
        self.wait_write("exit")

        self.wait_write("vrf definition clab-mgmt")
        self.wait_write("address-family ipv4")
        self.wait_write("exit")
        self.wait_write("description Management network")
        self.wait_write("exit")

        self.wait_write("interface GigabitEthernet0/0")
        self.wait_write("vrf forwarding clab-mgmt")
        self.wait_write("ip address 10.0.0.15 255.255.255.0")
        self.wait_write("no shutdown")
        self.wait_write("exit")
        self.wait_write("ip route vrf clab-mgmt 0.0.0.0 0.0.0.0 10.0.0.2")

        self.wait_write("crypto key generate rsa modulus 2048")
        self.wait_write("ip ssh version 2")

        self.wait_write("netconf ssh")
        self.wait_write("netconf max-sessions 16")
        self.wait_write("snmp-server community public rw")

        self.wait_write("no banner exec")
        self.wait_write("no banner login")
        self.wait_write("no banner incoming")

    def _load_startup_config(self):
        if not os.path.exists(STARTUP_CONFIG_FILE):
            self.logger.trace(f"Startup config file {STARTUP_CONFIG_FILE} not found")
            return

        self.logger.trace(f"Loading startup config file {STARTUP_CONFIG_FILE}")
        with open(STARTUP_CONFIG_FILE) as file:
            for line in (line.rstrip() for line in file):
                self.wait_write(line)

    def _save_config(self):
        self.logger.info("Saving configuration")

        self.wait_write("end")
        self.wait_write("write memory")


class VIOS(vrnetlab.VR):
    def __init__(self, hostname: str, username: str, password: str, conn_mode: str):
        super(VIOS, self).__init__(username, password)
        self.vms = [VIOS_vm(hostname, username, password, conn_mode)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable trace level logging",
        default=os.getenv("TRACE", "false").lower() == "true",
    )
    parser.add_argument(
        "--username", help="Username", default=os.getenv("USERNAME", "vrnetlab")
    )
    parser.add_argument(
        "--password", help="Password", default=os.getenv("PASSWORD", "VR-netlab9")
    )
    parser.add_argument(
        "--hostname", help="Router hostname", default=os.getenv("HOSTNAME", "vios")
    )
    parser.add_argument(
        "--connection-mode",
        help="Connection mode to use in the datapath",
        default=os.getenv("CONNECTION_MODE", "tc"),
    )
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = VIOS(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        conn_mode=args.connection_mode,
    )
    vr.start()
