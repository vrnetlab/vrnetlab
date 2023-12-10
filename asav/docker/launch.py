#!/usr/bin/env python3

import datetime
import logging
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


class ASAv_vm(vrnetlab.VM):
    def __init__(self, username, password, install_mode=False):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e

        super(ASAv_vm, self).__init__(
            username, password, disk_image=disk_image, ram=2048
        )
        self.nic_type = "e1000"
        self.install_mode = install_mode
        self.num_nics = 8

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"ciscoasa>"], 1)
        if match:  # got a match!
            if ridx == 0:  # login
                if self.install_mode:
                    self.logger.debug("matched, ciscoasa>")
                    self.wait_write("", wait=None)
                    self.wait_write("", None)
                    self.wait_write("", wait="ciscoasa>")
                    self.running = True
                    return

                self.logger.debug("matched, ciscoasa>")
                self.wait_write("", wait=None)

                # run main config!
                self.bootstrap_config()
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
        self.wait_write("enable", wait="ciscoasa>")
        self.wait_write("VR-netlab9", wait="Enter  Password:")
        self.wait_write("VR-netlab9", wait="Repeat Password:")
        self.wait_write("", wait="ciscoasa#")
        self.wait_write("configure terminal", wait="#")
        self.wait_write("N", wait="[Y]es, [N]o, [A]sk later:")
        self.wait_write("", wait="(config)#")
        self.wait_write("aaa authentication ssh console LOCAL")
        self.wait_write("aaa authentication enable console LOCAL")
        self.wait_write(
            "username %s password %s privilege 15" % (self.username, self.password)
        )
        self.wait_write("interface Management0/0")
        self.wait_write("nameif management")
        self.wait_write("ip address 10.0.0.15 255.255.255.0")
        self.wait_write("no shutdown")
        self.wait_write("ssh 0.0.0.0 0.0.0.0 management")
        self.wait_write("ssh version 2")
        self.wait_write("ssh key-exchange group dh-group14-sha256")
        self.wait_write("crypto key generate ecdsa")
        self.wait_write("write")
        self.wait_write("end")
        self.wait_write("\r", None)


class ASAv(vrnetlab.VR):
    def __init__(self, username, password):
        super(ASAv, self).__init__(username, password)
        self.vms = [ASAv_vm(username, password)]


class ASAv_installer(ASAv):
    """ASAv installer"""

    def __init__(self, username, password):
        super(ASAv, self).__init__(username, password)
        self.vms = [ASAv_vm(username, password, install_mode=True)]

    def install(self):
        self.logger.info("Installing ASAv")
        asav = self.vms[0]
        while not asav.running:
            asav.work()
        time.sleep(30)
        asav.stop()
        self.logger.info("Installation complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
    parser.add_argument("--install", action="store_true", help="Install ASAv")
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    if args.install:
        vr = ASAv_installer(args.username, args.password)
        vr.install()
    else:
        vr = ASAv(args.username, args.password)
        vr.start()
