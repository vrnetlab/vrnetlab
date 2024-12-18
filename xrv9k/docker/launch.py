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



class XRV_vm(vrnetlab.VM):
    def __init__(self, username, password, ram, nics, install_mode=False):
        disk_image = None
        for e in sorted(os.listdir("/")):
            if not disk_image and re.search(".qcow2", e):
                disk_image = "/" + e
        super(XRV_vm, self).__init__(username, password, disk_image=disk_image,
                                     ram=ram*1024)
        self.num_nics = nics
        self.install_mode = install_mode
        self.qemu_args.extend(["-cpu", "host",
                               "-smp", "cores=4,threads=1,sockets=1",
                               "-serial", "telnet:0.0.0.0:50%02d,server,nowait" % (self.num + 1),
                               "-serial", "telnet:0.0.0.0:50%02d,server,nowait" % (self.num + 2),
                               "-serial", "telnet:0.0.0.0:50%02d,server,nowait" % (self.num + 3)])
        self.credentials = [
                ['admin', 'admin']
            ]

        self.xr_ready = False

    def gen_mgmt(self):
        """ Generate qemu args for the mgmt interface(s)
        """
        res = []
        # mgmt interface
        res.extend(["-device", "virtio-net-pci,netdev=mgmt,mac=%s" % vrnetlab.gen_mac(0)])
        res.extend(["-netdev", "user,id=mgmt,net=10.0.0.0/24,tftp=/tftpboot,%s" % self.gen_host_forwards()])
        # dummy interface for xrv9k ctrl interface
        res.extend(["-device", "virtio-net-pci,netdev=ctrl-dummy,id=ctrl-dummy,mac=%s" % vrnetlab.gen_mac(0),
                    "-netdev", "tap,ifname=ctrl-dummy,id=ctrl-dummy,script=no,downscript=no"])
        # dummy interface for xrv9k dev interface
        res.extend(["-device", "virtio-net-pci,netdev=dev-dummy,id=dev-dummy,mac=%s" % vrnetlab.gen_mac(0),
                    "-netdev", "tap,ifname=dev-dummy,id=dev-dummy,script=no,downscript=no"])

        return res


    def bootstrap_spin(self):
        """ 
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"Press RETURN to get started",
            b"Not settable: Success",    # no SYSTEM CONFIGURATION COMPLETE in xrv9k?
            b"Enter root-system username",
            b"Username:", b"ios#"], 1)
        if match: # got a match!
            if ridx == 0: # press return to get started, so we press return!
                self.logger.debug("got 'press return to get started...'")
                self.wait_write("", wait=None)
            if ridx == 1: # system configuration complete
                self.logger.info("IOS XR system configuration is complete, should be able to proceed with bootstrap configuration")
                self.wait_write("", wait=None)
                self.xr_ready = True
            if ridx == 2: # initial user config
                if self.install_mode:
                    self.running = True
                    return
                self.logger.info("Creating initial user")
                self.wait_write(self.username, wait=None)
                self.wait_write(self.password, wait="Enter secret:")
                self.wait_write(self.password, wait="Enter secret again:")
                self.credentials.insert(0, [self.username, self.password])
            if ridx == 3: # matched login prompt, so should login
                self.logger.debug("matched login prompt")
                try:
                    username, password = self.credentials.pop(0)
                except IndexError as exc:
                    self.logger.error("no more credentials to try")
                    return
                self.logger.debug("trying to log in with %s / %s" % (username, password))
                self.wait_write(username, wait=None)
                self.wait_write(password, wait="Password:")
                self.logger.debug("logged in with %s / %s" % (username, password))
            if self.xr_ready == True and ridx == 4:
                # run main config!
                if not self.bootstrap_config():
                    # main config failed :/
                    self.logger.debug('bootstrap_config failed, restarting device')
                    self.stop()
                    self.start()
                    return

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

        self.wait_write("terminal length 0")

        self.wait_write("crypto key generate rsa")
        # check if we are prompted to overwrite current keys
        (ridx, match, res) = self.tn.expect([b"How many bits in the modulus",
            b"Do you really want to replace them",
            b"^[^ ]+#"], 10)
        if match: # got a match!
            if ridx == 0:
                self.wait_write("2048", None)
            elif ridx == 1: # press return to get started, so we press return!
                self.wait_write("no", None)

        # make sure we get our prompt back
        self.wait_write("")

        # wait for Gi0/0/0/0 in config
        if not self.wait_config("show interfaces description", "Gi0/0/0/0"):
            return False

        # Do not wait for call-home in 7.1.x and later, takes too long
        version =  self.version.split(".")
        if int(version[0]) < 7 or int(version[0]) == 7 and int(version[1]) < 1:
            if not self.wait_config("show running-config call-home", "service active"):
                return False

        self.wait_write("configure")
        # configure netconf
        self.wait_write("ssh server v2")
        self.wait_write("ssh server netconf port 830") # for 5.1.1
        self.wait_write("ssh server netconf vrf default") # for 5.3.3
        self.wait_write("ssh server rate-limit 600")
        self.wait_write("netconf agent ssh") # for 5.1.1
        self.wait_write("netconf-yang agent ssh") # for 5.3.3

        # configure xml agent
        self.wait_write("xml agent tty")

        # configure mgmt interface
        self.wait_write("interface MgmtEth 0/RP0/CPU0/0")
        self.wait_write("no shutdown")
        self.wait_write("ipv4 address 10.0.0.15/24")
        self.wait_write("exit")
        self.wait_write("commit")
        self.wait_write("exit")

        return True


class XRV_Installer(vrnetlab.VR_Installer):
    """ XRV installer

        Will start the XRV and then shut it down. Booting the XRV for the
        first time requires the XRV itself to install internal packages
        then it will restart. Subsequent boots will not require this restart.
        By running this "install" when building the docker image we can
        decrease the normal startup time of the XRV.
    """
    def __init__(self, username, password, ram, nics):
        super().__init__()
        self.vm = XRV_vm(username, password, ram, nics, install_mode=True)


class XRV(vrnetlab.VR):
    def __init__(self, username, password, ram, nics):
        super(XRV, self).__init__(username, password)
        self.vms = [ XRV_vm(username, password, ram, nics) ]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', default=vrnetlab.bool_from_env('TRACE'), action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default=os.getenv('USERNAME', 'vrnetlab'), help='Username')
    parser.add_argument('--password', default=os.getenv('PASSWORD', 'VR-netlab9'), help='Password')
    parser.add_argument('--install', default=vrnetlab.bool_from_env('INSTALL'), action='store_true', help='Initial install')
    parser.add_argument('--num-nics', type=int, default=int(os.getenv('NUM_NICS', 24)), help='Number of NICS')
    parser.add_argument('--ram', type=int, default=int(os.getenv('RAM', 16)), help='RAM in GB')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    if args.install:
        vr = XRV_Installer(args.username, args.password, args.ram, args.num_nics)
        vr.install()
    else:
        vr = XRV(args.username, args.password, args.ram, args.num_nics)
        vr.start()
