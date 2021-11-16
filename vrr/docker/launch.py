#!/usr/bin/env python3

import datetime
import logging
import os
import random
import re
import signal
import sys
import telnetlib
import time
import math

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


class VRR_vm(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search(".vmdk", e):
                disk_image = "/" + e
        super(VRR_vm, self).__init__(
            username, password, disk_image=disk_image, ram=2048
        )
        self.num_nics = 2
        self.smbios = ["type=1,product=VRR"]

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.logger.warning("no output from serial console, restarting VRR")
            self.stop()
            self.start()
            self.spins = 0
            return

        (ridx, match, res) = self.tn.expect([b"login:", b"root@(%|:~ #)"], 1)
        if match:  # got a match!
            if ridx == 0:  # matched login prompt, so should login
                self.logger.info("matched login prompt")
                self.wait_write("root", wait=None)
            if ridx == 1:
                # run main config!
                self.bootstrap_config()
                self.running = True
                self.tn.close()
                # calc startup time
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s" % startup_time)
                return

        else:
            # no match, if we saw some output from the router it's probably
            # booting, so let's give it some more time
            if res != b"":
                self.logger.trace("OUTPUT VCP: %s" % res.decode())
                # reset spins if we saw some output
                self.spins = 0

        self.spins += 1

        return

    def bootstrap_config(self):
        """Do the actual bootstrap config"""
        self.wait_write("cli", None)
        time.sleep(90)
        self.wait_write("configure", ">", 10)
        self.wait_write("set system services ssh")
        self.wait_write("set system services netconf ssh")
        self.wait_write("set system services netconf rfc-compliant")
        self.wait_write(
            "set system login user %s class super-user authentication plain-text-password"
            % self.username
        )
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("set system root-authentication plain-text-password")
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("set interfaces em0 unit 0 family inet address 10.0.0.15/24")
        self.wait_write("delete interfaces em0 unit 0 family inet dhcp")
        self.wait_write("delete interfaces em1 unit 0 family inet dhcp")
        self.wait_write("delete interfaces em2 unit 0 family inet dhcp")
        self.wait_write("delete system processes dhcp-service")
        self.wait_write("delete chassis auto-image-upgrade")
        self.wait_write("commit")
        self.wait_write("exit")

    def wait_write(self, cmd, wait="#", timeout=None):
        """Wait for something and then send command"""
        if wait:
            self.logger.trace("Waiting for %s" % wait)
            while True:
                (ridx, match, res) = self.tn.expect(
                    [wait.encode(), b"Retry connection attempts"], timeout=timeout
                )
                if match:
                    if ridx == 0:
                        break
                    if ridx == 1:
                        self.tn.write("yes\r".encode())
            self.logger.trace("Read: %s" % res.decode())
        self.logger.debug("writing to serial console: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())


class VRR(vrnetlab.VR):
    def __init__(self, username, password):
        super(VRR, self).__init__(username, password)
        self.vms = [VRR_vm(username, password)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = VRR(args.username, args.password)
    vr.start()
