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


class PAN_vm(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode):
        disk_image = ""
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        if disk_image == "":
            logging.getLogger().info("Disk image was not found")
            exit(1)
        super(PAN_vm, self).__init__(
            username, password, disk_image=disk_image, ram=6144, cpu="host,level=9", smp="2,sockets=1,cores=1"
        )
        self.hostname = hostname
        self.conn_mode = conn_mode
        # mgmt + 24 that show up in the vm, may as well populate them all in vrnetlab right away
        self.num_nics = 25
        self.nic_type = "virtio-net-pci"
        # pan wants a uuid it seems (for licensing reasons?!)
        self.uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.logger.info("To many spins with no result, restarting")
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect(
            [
                b"Login incorrect",
                b"vm login:",
                b"PA-HDF login",
                b"PA-VM login:",
                b"[pP]assword:",
                b"Enter old password :",
                b"Enter new password :",
                b"Confirm password   :",
                b"admin@PA-VM>",
            ],
            1,
        )
        if match:  # got a match!
            if ridx == 0:
                self.logger.debug("login incorrect, sleeping a bit")
                time.sleep(30)
            if ridx == 1:
                self.wait_write("", wait=None)
                time.sleep(30)
            elif ridx == 2:  # PA-HDF login
                self.wait_write("", wait=None)
                time.sleep(30)
            elif ridx == 3:  # login
                self.logger.debug("sending username 'admin'")
                self.wait_write("admin", wait=None)
            elif ridx == 4:
                self.logger.debug("sending password 'admin'")
                self.wait_write("admin", wait=None)
            elif ridx == 5:
                self.logger.debug("sending 'old' password 'admin'")
                self.wait_write("admin", wait=None)
            elif ridx == 6:
                self.logger.debug(f"sending 'new' password '{self.password}'")
                self.wait_write(self.password, wait=None)
            elif ridx == 7:
                self.logger.debug(f"confirming 'new' password '{self.password}'")
                self.wait_write(self.password, wait=None)
            elif ridx == 8:
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

        # disable paging/fancy terminal stuff
        self.wait_write("set cli pager off", ">")
        self.wait_write("set cli scripting-mode on", ">")

        # wait for auto commit to finish, seems like pan wants a kick here w/ a return for
        # whatever reason
        self.wait_write("", None)
        while True:
            (ridx, match, res) = self.tn.expect([b"FIN", b"PEND"], 1)
            if match:
                if ridx == 0:  # login
                    self.logger.debug("auto commit complete, begin configuration")
                    break
                elif ridx == 1:
                    self.logger.debug("auto commit still pending, sleeping...")
                    time.sleep(10)
                    self.wait_write("show jobs processed", wait=None)
            elif res == b"":
                time.sleep(10)
                self.wait_write("show jobs processed", wait=None)

        self.logger.debug("applying mgmt addressing and credentials...")
        self.wait_write("configure", wait=None)

        # configure mgmt interface
        self.wait_write(
            "set deviceconfig system ip-address 10.0.0.15 netmask 255.255.255.0 default-gateway 10.0.0.2",
            "#",
        )

        # configure mgmt user
        self.wait_write(f"set mgt-config users {self.username} password")
        self.wait_write(self.password, "Enter password   :")
        self.wait_write(self.password, "Confirm password :")
        self.wait_write(f"set mgt-config users {self.username} permissions role-based superuser yes")

        self.logger.debug("committing changes...")
        self.wait_write("commit", "#")

        time.sleep(60)
        self.wait_write("exit", "#")

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

        self.wait_write("configure", wait=None)

        for line in config_lines:
            self.wait_write(line, "#")

        self.logger.debug("committing user config...")
        self.wait_write("commit", "#")
        self.wait_write("exit", "#")


class PAN(vrnetlab.VR):
    def __init__(self, hostname, username, password, conn_mode):
        super(PAN, self).__init__(username, password)
        self.vms = [PAN_vm(hostname, username, password, conn_mode)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--hostname", default="vr-pan", help="Router hostname")
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

    vr = PAN(args.hostname, args.username, args.password, args.connection_mode)
    vr.start()
