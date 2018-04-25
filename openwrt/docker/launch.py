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

class OpenWRT_vm(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search(".img$", e):
                disk_image = "/" + e
        super(OpenWRT_vm, self).__init__(username, password, disk_image=disk_image, ram=128)
        self.nic_type = "virtio-net-pci"
        self.num_nics = 1

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"br-lan"], 1)
        if match: # got a match!
            if ridx == 0: # login
                self.logger.debug("VM started")
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
        # Get a prompt
        self.wait_write("\r", None)
        # Configure interface
        self.wait_write("ifconfig br-lan 10.0.0.15 netmask 255.255.255.0", "#")
        # Set root password (ssh login prerequisite)
        self.wait_write("passwd", "#")
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype password:")
        # Create vrnetlab user
        self.wait_write("echo '%s:x:501:501:%s:/home/%s:/bin/ash' >> /etc/passwd" %(self.username, self.username, self.username), "#")
        self.wait_write("passwd %s" %(self.username))
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype password:")
        # Add user to root group
        self.wait_write("sed -i '1d' /etc/group", "#")
        self.wait_write("sed -i '1i root:x:0:%s' /etc/group" % (self.username))
        # Create home dir
        self.wait_write("mkdir -p /home/%s" %(self.username))
        self.wait_write("chown %s /home/%s" %(self.username, self.username))
        self.logger.info("completed bootstrap configuration")

class OpenWRT(vrnetlab.VR):
    def __init__(self, username, password):
        super(OpenWRT, self).__init__(username, password)
        self.vms = [ OpenWRT_vm(username, password) ]

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

    vr = OpenWRT(args.username, args.password)
    vr.start()
