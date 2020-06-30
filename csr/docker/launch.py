#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import subprocess
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



class CSR_vm(vrnetlab.VM):
    def __init__(self, username, password, install_mode=False, meshnet=False):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
            if re.search("\.license$", e):
                os.rename("/" + e, "/tftpboot/license.lic")

        self.license = False
        if os.path.isfile("/tftpboot/license.lic"):
            logger.info("License found")
            self.license = True

        super(CSR_vm, self).__init__(username, password, disk_image=disk_image)

        self.install_mode = install_mode
        self.num_nics = 9
        self.meshnet = meshnet

        if self.install_mode:
            logger.trace("install mode")
            self.image_name = "config.iso"
            self.create_boot_image()

            self.qemu_args.extend(["-cdrom", "/" +self.image_name]) 


    def create_boot_image(self):
        """ Creates a iso image with a bootstrap configuration
        """

        cfg_file = open('/iosxe_config.txt', 'w')
        if self.license:
            cfg_file.write("do clock set 13:33:37 1 Jan 2010\r\n")
            cfg_file.write("interface GigabitEthernet1\r\n")
            cfg_file.write("ip address 10.0.0.15 255.255.255.0\r\n")
            cfg_file.write("no shut\r\n")
            cfg_file.write("exit\r\n")
            cfg_file.write("license accept end user agreement\r\n")
            cfg_file.write("yes\r\n")
            cfg_file.write("do license install tftp://10.0.0.2/license.lic\r\n\r\n")

        cfg_file.write("platform console serial\r\n\r\n")
        cfg_file.write("do wr\r\n")
        cfg_file.write("do reload\r\n")
        cfg_file.close()

        genisoimage_args = ["genisoimage", "-l", "-o", "/" + self.image_name, "/iosxe_config.txt"]

        subprocess.Popen(genisoimage_args)


    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"Press RETURN to get started!"], 1)
        if match: # got a match!
            if ridx == 0: # login
                if self.install_mode:
                    self.running = True
                    return

                self.logger.debug("matched, Press RETURN to get started.")
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
        self.wait_write("enable", wait=">")
        self.wait_write("configure terminal", wait=">")

        self.wait_write("hostname csr1000v")
        self.wait_write("username %s privilege 15 password %s" % (self.username, self.password))
        self.wait_write("ip domain-name example.com")
        self.wait_write("crypto key generate rsa modulus 2048")

        self.wait_write("interface GigabitEthernet1")
        self.wait_write("ip address 10.0.0.15 255.255.255.0")
        self.wait_write("no shut")
        self.wait_write("exit")
        self.wait_write("restconf")
        self.wait_write("netconf-yang")

        self.wait_write("line vty 0 4")
        self.wait_write("login local")
        self.wait_write("transport input all")
        self.wait_write("end")
        self.wait_write("copy running-config startup-config")
        self.wait_write("\r", None)


class CSR(vrnetlab.VR):
    def __init__(self, username, password, meshnet=False):
        super(CSR, self).__init__(username, password)
        self.vms = [ CSR_vm(username, password, meshnet=meshnet) ]


class CSR_installer(CSR):
    """ CSR installer
        
        Will start the CSR with a mounted iso to make sure that we get
        console output on serial, not vga.
    """
    def __init__(self, username, password):
        super(CSR, self).__init__(username, password)
        self.vms = [ CSR_vm(username, password, install_mode=True)  ]

    def install(self):
        self.logger.info("Installing CSR")
        csr = self.vms[0]
        while not csr.running:
            csr.work()
        time.sleep(30)
        csr.stop()
        self.logger.info("Installation complete")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    parser.add_argument('--install', action='store_true', help='Install CSR')
    parser.add_argument('--meshnet', action='store_true', help='Native docker networking')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    if args.install:
        vr = CSR_installer(args.username, args.password)
        vr.install()
    else:
        vr = CSR(args.username, args.password, meshnet=args.meshnet)
        vr.start()
