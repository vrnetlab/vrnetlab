#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import sys
import telnetlib

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

class ROS_vm(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search(".vmdk$", e):
                disk_image = "/" + e
        super(ROS_vm, self).__init__(username, password, disk_image=disk_image, ram=256)
        self.qemu_args.extend(["-boot", "n"])

        self.num_nics = 31

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"MikroTik Login"], 1)
        if match: # got a match!
            if ridx == 0: # login
                self.logger.debug("VM started")

                # Login
                self.wait_write("\r", None)
                # Append +ct to username for the plain-text console version
                self.wait_write("admin+ct", wait="MikroTik Login: ")
                self.wait_write("", wait="Password: ")
                self.wait_write("n", wait="Do you want to see the software license? [Y/n]: ")

                self.logger.debug("Login completed")

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
        if res != b'':
            self.logger.trace("OUTPUT: %s" % res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return

    def bootstrap_config(self):
        """ Do the actual bootstrap config
        """
        self.logger.info("applying bootstrap configuration")
        self.wait_write("/ip address add interface=ether1 address=10.0.0.15 netmask=255.255.255.0", "[admin@MikroTik] > ")
        self.wait_write("/user add name=%s password=\"%s\" group=full" % (self.username, self.password), "[admin@MikroTik] > ")
        self.wait_write("\r", "[admin@MikroTik] > ")
        self.logger.info("completed bootstrap configuration")

class ROS(vrnetlab.VR):
    def __init__(self, username, password):
        super(ROS, self).__init__(username, password)
        self.vms = [ ROS_vm(username, password) ]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = ROS(args.username, args.password)
    vr.start()
