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


class NXOS_vm(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        super(NXOS_vm, self).__init__(username, password, disk_image=disk_image, ram=6144)
        overlay_disk_image = re.sub(r'(\.[^.]+$)', r'-overlay\1', disk_image)
        self.num_nics = 8
        self.qemu_args.extend(["-bios", "/OVMF.fd"])  # bios for n9kv
        self.qemu_args.extend(["-boot", "c"])  # boot harddrive first
        replace_index = self.qemu_args.index("if=ide,file={}".format(overlay_disk_image))
        self.qemu_args[replace_index] = "file={},if=none,id=drive-sata-disk0,format=qcow2".format(overlay_disk_image)
        self.qemu_args.extend(["-device", "ahci,id=ahci0,bus=pci.0"])
        self.qemu_args.extend(["-device", "ide-drive,drive=drive-sata-disk0,bus=ahci0.0,id=drive-sata-disk0,bootindex=1"])
        self.credentials = [
                ['admin', 'admin']
            ]

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """
        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"\(yes\/skip\/no\)\[no\]:", b"login:"], 1)
        if match:  # got a match!
            if ridx == 0:
                self.logger.debug("matched poap prompt")
                self.wait_write("yes", wait=None)
                self.wait_write("no", wait="Do you want to enforce secure password standard")
                self.wait_write("admin", wait="Enter the password for \"admin\"")
                self.wait_write("admin", wait="Confirm the password for \"admin\"")
                self.wait_write("no", wait="Would you like to enter the basic configuration dialog")
            elif ridx == 1:  # login
                self.logger.debug("matched login prompt")
                try:
                    username, password = self.credentials.pop(0)
                except IndexError as exc:
                    self.logger.error("no more credentials to try... {}".format(exc))
                    return
                self.logger.debug("trying to log in with %s / %s" % (username, password))
                self.wait_write(username, wait=None)
                self.wait_write(password, wait="Password:")

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
        self.wait_write("", None)
        self.wait_write("configure")
        self.wait_write("username %s password 0 %s role network-admin" % (self.username, self.password))

        # configure mgmt interface
        self.wait_write("interface mgmt0")
        self.wait_write("ip address 10.0.0.15/24")
        self.wait_write("exit")
        self.wait_write("exit")
        self.wait_write("copy running-config startup-config")


class NXOS(vrnetlab.VR):
    def __init__(self, username, password):
        super(NXOS, self).__init__(username, password)
        self.vms = [NXOS_vm(username, password)]


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

    vr = NXOS(args.username, args.password)
    vr.start()
