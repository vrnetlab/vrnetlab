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



class VQFX_vcp(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search("-re-.*.vmdk", e):
                vrnetlab.run_command(["qemu-img", "create", "-b", "/" + e, "-f", "qcow", "/vcp.qcow2"])
        super(VQFX_vcp, self).__init__(username, password, disk_image="/vcp.qcow2", ram=2048)
        self.num_nics = 12


    def start(self):
        # use parent class start() function
        super(VQFX_vcp, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(["brctl", "addif", "int_cp", "vcp-int"])
        vrnetlab.run_command(["ip", "link", "set", "vcp-int", "up"])


    def gen_mgmt(self):
        """ Generate mgmt interface(s)

            We override the default function since we want a virtio NIC to the
            vFPC
        """
        # call parent function to generate first mgmt interface (e1000)
        res = super(VQFX_vcp, self).gen_mgmt()
        # add virtio NIC for internal control plane interface to vFPC
        res.append("-device")
        res.append("e1000,netdev=vcp-int,mac=%s" % vrnetlab.gen_mac(1))
        res.append("-netdev")
        res.append("tap,ifname=vcp-int,id=vcp-int,script=no,downscript=no")

        # dummy
        for i in range(1):
            res.append("-device")
            res.append("e1000,netdev=dummy%d,mac=%s" % (i, vrnetlab.gen_mac(1)))
            res.append("-netdev")
            res.append("tap,ifname=dummy%d,id=dummy%d,script=no,downscript=no" % (i, i))

        return res



    def bootstrap_spin(self):
        """ This function should be called periodically to do work.

            returns False when it has failed and given up, otherwise True
        """
        if self.spins > 300:
            # too many spins with no result -> restart
            self.logger.warning("no output from serial console, restarting VCP")
            self.stop()
            self.start()
            self.spins = 0
            return

        (ridx, match, res) = self.tn.expect([b"login:", b"root@vqfx-re:RE:0%"], 1)
        if match: # got a match!
            if ridx == 0: # matched login prompt, so should login
                self.logger.info("matched login prompt")
                self.wait_write("root", wait=None)
                self.wait_write("Juniper", wait="Password:")
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
            if res != b'':
                self.logger.trace("OUTPUT VCP: %s" % res.decode())
                # reset spins if we saw some output
                self.spins = 0

        self.spins += 1



    def bootstrap_config(self):
        """ Do the actual bootstrap config
        """
        self.wait_write("cli", None)
        self.wait_write("configure", '>', 10)
        self.wait_write("set system services ssh")
        self.wait_write("set system services netconf ssh")
        self.wait_write("set system services netconf rfc-compliant")
        self.wait_write("delete system login user vagrant")
        self.wait_write("set system login user %s class super-user authentication plain-text-password" % self.username)
        self.wait_write(self.password, 'New password:')
        self.wait_write(self.password, 'Retype new password:')
        self.wait_write("set system root-authentication plain-text-password")
        self.wait_write(self.password, 'New password:')
        self.wait_write(self.password, 'Retype new password:')
        self.wait_write("delete interfaces")
        self.wait_write("set interfaces em0 unit 0 family inet address 10.0.0.15/24")
        self.wait_write("set interfaces em1 unit 0 family inet address 169.254.0.2/24")
        self.wait_write("commit")
        self.wait_write("exit")


    def wait_write(self, cmd, wait='#', timeout=None):
        """ Wait for something and then send command
        """
        if wait:
            self.logger.trace("Waiting for %s" % wait)
            while True:
                (ridx, match, res) = self.tn.expect([wait.encode(), b"Retry connection attempts"], timeout=timeout)
                if match:
                    if ridx == 0:
                        break
                    if ridx == 1:
                        self.tn.write("yes\r".encode())
            self.logger.trace("Read: %s" % res.decode())
        self.logger.debug("writing to serial console: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())





class VQFX_vpfe(vrnetlab.VM):
    def __init__(self):
        for e in os.listdir("/"):
            if re.search("-pfe-.*.vmdk", e):
                vrnetlab.run_command(["qemu-img", "create", "-b", "/" + e, "-f", "qcow", "/vpfe.qcow2"])
        super(VQFX_vpfe, self).__init__(None, None, disk_image="/vpfe.qcow2", num=1, ram=2048)
        self.num_nics = 0


    def gen_mgmt(self):
        res = []
        # mgmt interface
        res.extend(["-device", "e1000,netdev=mgmt,mac=%s" % vrnetlab.gen_mac(0)])
        res.extend(["-netdev", "user,id=mgmt,net=10.0.0.0/24"])
        # internal control plane interface to vFPC
        res.extend(["-device", "e1000,netdev=vpfe-int,mac=%s" %
                    vrnetlab.gen_mac(0)])
        res.extend(["-netdev",
                    "tap,ifname=vpfe-int,id=vpfe-int,script=no,downscript=no"])

        return res



    def start(self):
        # use parent class start() function
        super(VQFX_vpfe, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(["brctl", "addif", "int_cp", "vpfe-int"])
        vrnetlab.run_command(["ip", "link", "set", "vpfe-int", "up"])



    def bootstrap_spin(self):
        self.running = True
        self.tn.close()
        return



class VQFX(vrnetlab.VR):
    """ Juniper vMX router
    """

    def __init__(self, username, password):
        super(VQFX, self).__init__(username, password)

        self.vms = [ VQFX_vcp(username, password), VQFX_vpfe() ]

        # set up bridge for connecting VCP with vFPC
        vrnetlab.run_command(["brctl", "addbr", "int_cp"])
        vrnetlab.run_command(["ip", "link", "set", "int_cp", "up"])



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    parser.add_argument('--install', action='store_true', help='Install vMX')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = VQFX(args.username, args.password)
    vr.start()
