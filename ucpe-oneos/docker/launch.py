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



class UCPE_vm(vrnetlab.VM):
    def __init__(self, username, password, uuid, license_key, license_activate):
        disk_image = None
        for e in sorted(os.listdir("/")):
            if not disk_image and re.search(".qcow2$", e):
                disk_image = "/" + e
        super(UCPE_vm, self).__init__(username, password, disk_image=disk_image, ram=9216)
        self.num_nics = 20
        self.nic_type = "virtio-net-pci"
        self.uuid = uuid
        self.qemu_args.extend(["-cpu", "host", "-smp", "4"])
        self.license_key = license_key
        self.license_activate = license_activate

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.logger.info("To many spins with no result, restarting")
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"Username:"], 1)
        if match: # got a match!
            if ridx == 0: # login
                self.logger.debug("matched login prompt")
                self.logger.debug("trying to log in with 'admin'")
                self.wait_write("admin", wait=None)
                self.wait_write("admin", wait="Password:")

                # run main config!
                startup_config = os.getenv('STARTUP_CONFIG')
                if startup_config:
                    self.insert_startup_config(startup_config)
                else:
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
        self.wait_write("config terminal")
        self.wait_write(f"username {self.username} password {self.password} administrator encrypted 0 type 2")
        self.wait_write("interface gigabitethernet 0/0")
        self.wait_write("ip address 10.0.0.15 255.255.255.0")
        if self.license_key:
            for key in self.license_key:
                self.wait_write(f"license key add {key}")
        if self.license_activate:
            for feature in self.license_activate:
                self.wait_write(f"license activate {feature}")
        self.wait_write("commit and-quit")

        self.wait_write("paginate false")
        self.wait_write("show version")
        self.wait_write("show product-info-area")
        self.wait_write("show ovp cpu")
        self.wait_write("show license")
        self.wait_write("")
        self.wait_write("")

    def insert_startup_config(self, startup_config):
        self.logger.debug('startup_config = ' + startup_config)
        self.wait_write("config terminal")
        for line in startup_config.split('\n'):
            self.wait_write(line)
        self.wait_write("commit and-quit")
        self.wait_write("")
        self.wait_write("")


class UCPE(vrnetlab.VR):
    def __init__(self, username, password, uuid, license_key, license_activate):
        super(UCPE, self).__init__(username, password)
        self.vms = [ UCPE_vm(username, password, uuid, license_key, license_activate) ]


def _warn_startup_override(args, logger):
    if os.getenv("STARTUP_CONFIG"):
        for arg in ("username", "password", "license-key", "license-activate"):
            val = getattr(args, arg.replace("-", "_"))
            if val:
                logger.warning(f"When STARTUP_CONFIG is provided the bootstrap script does not use the '{arg}' argument. Please ensure the desired value {arg}='{val}' is part of STARTUP_CONFIG")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', default=vrnetlab.bool_from_env('TRACE'), action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default=os.getenv('USERNAME', 'vrnetlab'), help='Username')
    parser.add_argument('--password', default=os.getenv('PASSWORD', 'VR-netlab9'), help='Password')
    parser.add_argument('--uuid', default=os.getenv('UUID'), help='Set UUID to a static value (for applying license)')
    parser.add_argument('--license-key', nargs='*', default=vrnetlab.list_from_env('LICENSE_KEY'), help='One or more license keys to apply at bootstrap')
    parser.add_argument('--license-activate', nargs='+', default=vrnetlab.list_from_env('LICENSE_ACTIVATE'), help='One or more licensed features to activate at bootstrap')
    args = parser.parse_args()

    if args.license_key and not args.license_activate:
        license_activate = ['open-virtualization']
    else:
        license_activate = args.license_activate

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)
    _warn_startup_override(args, logger)

    vr = UCPE(args.username, args.password, args.uuid, args.license_key, license_activate)
    vr.start()
