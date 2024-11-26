#!/usr/bin/env python3

import datetime
import logging
import math
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



class VEOS_vm(vrnetlab.VM):
    def __init__(self, username, password):
        disk_image = None
        for e in sorted(os.listdir("/")):
            if not disk_image and re.search(".vmdk$", e):
                disk_image = "/" + e
        for e in sorted(os.listdir("/")):
            if re.search(".iso$", e):
                boot_iso = "/" + e
        super(VEOS_vm, self).__init__(username, password, disk_image=disk_image, ram=2048)
        self.num_nics = 20
        self.qemu_args.extend(["-cdrom", boot_iso, "-boot", "d"])


    def gen_mgmt(self):
        """ Generate qemu args for the mgmt interface(s)
        """
        res = []
        # mgmt interface is special - we use qemu user mode network
        res.append("-device")
        # vEOS-lab requires its Ma1 interface to be the first in the bus, so let's hardcode it
        res.append(self.nic_type + ",netdev=p%(i)02d,mac=%(mac)s,bus=pci.1,addr=0x2"
                    % { 'i': 0, 'mac': vrnetlab.gen_mac(0) })
        res.append("-netdev")
        res.append("user,id=p%(i)02d,net=10.0.0.0/24,tftp=/tftpboot,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=udp::2161-10.0.0.15:161,hostfwd=tcp::2830-10.0.0.15:830,hostfwd=tcp::2080-10.0.0.15:80,hostfwd=tcp::2443-10.0.0.15:443" % { 'i': 0 })

        return res


    def gen_nics(self):
        """ Generate qemu args for the normal traffic carrying interface(s)
        """
        res = []
        # vEOS-lab requires its Ma1 interface to be the first in the bus, so start normal nics at 2
        for i in range(2, self.num_nics+1):
            # calc which PCI bus we are on and the local add on that PCI bus
            pci_bus = math.floor(i/self.nics_per_pci_bus) + 1
            addr = (i % self.nics_per_pci_bus) + 1

            # decrement i to make interfaces line up
            i = i-1
            res.append("-device")
            res.append("%(nic_type)s,netdev=p%(i)02d,mac=%(mac)s,bus=pci.%(pci_bus)s,addr=0x%(addr)x" % {
                       'nic_type': self.nic_type,
                       'i': i,
                       'pci_bus': pci_bus,
                       'addr': addr,
                       'mac': vrnetlab.gen_mac(i)
                    })
            res.append("-netdev")
            res.append("socket,id=p%(i)02d,listen=:%(j)02d"
                       % { 'i': i, 'j': i + 10000 })
        return res

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.logger.info("To many spins with no result, restarting")
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"login:"], 1)
        if match: # got a match!
            if ridx == 0: # login
                self.logger.debug("matched login prompt")
                self.logger.debug("trying to log in with 'admin'")
                self.wait_write("admin", wait=None)

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
        self.wait_write("enable", ">")
        self.wait_write("configure")
        self.wait_write("username %s secret 0 %s role network-admin" % (self.username, self.password))

        # configure mgmt interface
        self.wait_write("interface Management 1")
        self.wait_write("ip address 10.0.0.15/24")
        self.wait_write("exit")
        self.wait_write("management api http-commands")
        self.wait_write("protocol unix-socket")
        self.wait_write("no shutdown")
        self.wait_write("exit")
        self.wait_write("exit")
        self.wait_write("copy running-config startup-config")



class VEOS(vrnetlab.VR):
    def __init__(self, username, password):
        super(VEOS, self).__init__(username, password)
        self.vms = [ VEOS_vm(username, password) ]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', default=vrnetlab.bool_from_env('TRACE'), action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default=os.getenv('USERNAME', 'vrnetlab'), help='Username')
    parser.add_argument('--password', default=os.getenv('PASSWORD', 'VR-netlab9'), help='Password')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = VEOS(args.username, args.password)
    vr.start()
