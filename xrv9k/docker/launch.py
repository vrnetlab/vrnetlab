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
    def __init__(self, username, password, ram, nics):
        for e in os.listdir("/"):
            if re.search(".qcow2", e):
                disk_image = "/" + e
        super(XRV_vm, self).__init__(username, password, disk_image=disk_image,
                                     ram=ram*1024)
        self.num_nics = nics
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
        if not self._wait_config("show interfaces description", "Gi0/0/0/0"):
            return False

        # wait for call-home in config
        if not self._wait_config("show running-config call-home", "service active"):
            return False

        self.wait_write("configure")
        # configure netconf
        self.wait_write("ssh server v2")
        self.wait_write("ssh server netconf port 830") # for 5.1.1
        self.wait_write("ssh server netconf vrf default") # for 5.3.3
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

    def _wait_config(self, show_cmd, expect):
        """ Some configuration takes some time to "show up".
            To make sure the device is really ready, wait here.
        """
        self.logger.debug('waiting for {} to appear in {}'.format(expect, show_cmd))
        wait_spins = 0
        # 10s * 90 = 900s = 15min timeout
        while wait_spins < 90:
            self.wait_write(show_cmd, wait=None)
            _, match, data = self.tn.expect([expect.encode('UTF-8')], timeout=10)
            self.logger.trace(data.decode('UTF-8'))
            if match:
                self.logger.debug('a wild {} has appeared!'.format(expect))
                return True
            wait_spins += 1
        self.logger.error('{} not found in {}'.format(expect, show_cmd))
        return False


class XRV(vrnetlab.VR):
    def __init__(self, username, password, ram, nics):
        super(XRV, self).__init__(username, password)
        self.vms = [ XRV_vm(username, password, ram, nics) ]



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    parser.add_argument('--num-nics', type=int, default=24, help='Number of NICS')
    parser.add_argument('--ram', type=int, default=16, help='RAM in GB')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = XRV(args.username, args.password, args.ram, args.num_nics)
    vr.start()
