#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import sys

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

class VSRX_vm(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        super(VSRX_vm, self).__init__(username, password, disk_image=disk_image, ram=4096)
        self.qemu_args.extend(["-smp", "2"])
        self.nic_type = "virtio-net-pci"
        self.conn_mode = conn_mode
        self.num_nics = 10
        self.hostname = hostname

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"login:"], 1)
        if match: # got a match!
            if ridx == 0: # login
                self.logger.info("VM started")

                # Login
                self.wait_write("\r", None)
                self.wait_write("root", wait="login:")
                self.wait_write("", wait="root@:~ # ")
                self.logger.info("Login completed")

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
        self.wait_write("cli", "#")
        self.wait_write("configure", ">")
        self.wait_write("top delete", "#")
        self.wait_write("yes", "Delete everything under this level? [yes,no] (no) ")
        self.wait_write("set system services ssh", "#")
        self.wait_write("set system services netconf ssh", "#")
        self.wait_write("set system login user %s class super-user authentication plain-text-password" % ( self.username ), "#")
        self.wait_write("set system management-instance", "#")
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("set system root-authentication plain-text-password", "#")
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("set interfaces fxp0 unit 0 family inet address 10.0.0.15/24", "#")
        self.wait_write("commit and-quit", "#")
        self.logger.info("completed bootstrap configuration")

class VSRX(vrnetlab.VR):
    def __init__(self, hostname, username, password, conn_mode):
        super(VSRX, self).__init__(username, password)
        self.vms = [ VSRX_vm(hostname, username, password, conn_mode) ]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--trace", action="store_true", help="enable trace level logging")
    parser.add_argument("--hostname", default="vr-vsrx", help="SRX hostname")
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
    parser.add_argument("--connection-mode", default="tc", help="Connection mode to use in the datapath")
    args = parser.parse_args()


    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = VSRX(args.hostname,
        args.username,
        args.password,
        conn_mode=args.connection_mode,
    )
    vr.start()
