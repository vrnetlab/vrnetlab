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
from ipaddress import IPv4Interface

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
    def __init__(self, username, password, install_mode=False, **kwargs):
        disk_image = None
        for e in sorted(os.listdir("/")):
            if not disk_image and re.search(r".qcow2$", e):
                disk_image = "/" + e

        super(CSR_vm, self).__init__(username, password, disk_image=disk_image, ram=8192)

        self.install_mode = install_mode
        self.organization_name = kwargs.get('organization_name')
        self.sp_organization_name = kwargs.get('sp_organization_name')
        self.vbond = kwargs.get('vbond')
        self.system_ip = kwargs.get('system_ip')
        self.transport_ipv4_address = kwargs.get('transport_ipv4_address')
        self.transport_ipv4_gateway = kwargs.get('transport_ipv4_gateway')
        self.site_id = kwargs.get('site_id')
        self.num_nics = 9
        # Use vmxnet3 instead of virtio-net-pci to make dot1Q encapsulation
        # work. With other NIC types the router ignores tagged frames.
        self.nic_type = "vmxnet3"

        if self.install_mode:
            logger.trace("install mode")
            self.image_name = "config.iso"
            self.create_boot_image()

            self.qemu_args.extend(["-cdrom", "/" +self.image_name])
        else:
            self.qemu_args.extend(["-cpu", "host",
                                   "-smp", "2"])

    def create_boot_image(self):
        """ Creates a iso image with a bootstrap configuration
        """

        cfg_file = open('/iosxe_config.txt', 'w')
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
                self.logger.debug("matched, Press RETURN to get started.")

                if self.install_mode:
                    self.wait_write("", wait=None)
                    self.wait_write("enable", wait=">")
                    self.wait_write("clear platform software vnic-if nvtable")
                    self.wait_write("controller-mode enable")
                    self.wait_write("", wait="[confirm]")
                    self.wait_write("no", wait="(yes/[no]):")
                    self.running = True
                    return

                self.wait_write("", wait=None)
                self.wait_write("admin", wait="Username:")
                self.wait_write("admin", wait="Password:")
                self.wait_write("admin", wait="Enter new password:")
                self.wait_write("admin", wait="Confirm password:")
                self.wait_write("", wait="Successfully set new admin password")

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
        transport_ipv4_address = IPv4Interface(self.transport_ipv4_address)

        self.logger.info("applying bootstrap configuration")
        self.wait_write("")
        self.wait_write("config-transaction")
        self.wait_write("username  %s privilege 15 secret %s" % (self.username, self.password), wait="(config)#")
        self.wait_write("system system-ip %s" % (self.system_ip))
        self.wait_write("site-id %s" % (self.site_id))
        self.wait_write("organization-name \"%s\"" % (self.organization_name))
        self.wait_write("sp-organization-name \"%s\"" % (self.sp_organization_name))
        self.wait_write("vbond %s" % (self.vbond))
        self.wait_write("top")
        self.wait_write("interface GigabitEthernet1")
        self.wait_write("ip address 10.0.0.15 255.255.255.0")
        self.wait_write("no shutdown")
        self.wait_write("top")
        self.wait_write("interface GigabitEthernet2")
        self.wait_write("ip address %s %s" % (transport_ipv4_address.ip, transport_ipv4_address.netmask))
        self.wait_write("no shutdown")
        self.wait_write("top")
        self.wait_write("interface Tunnel2")
        self.wait_write("no shutdown")
        self.wait_write("ip unnumbered GigabitEthernet2")
        self.wait_write("tunnel source GigabitEthernet2")
        self.wait_write("tunnel mode sdwan")
        self.wait_write("top")
        self.wait_write("sdwan")
        self.wait_write("interface GigabitEthernet2")
        self.wait_write("tunnel-interface")
        self.wait_write("encapsulation ipsec")
        self.wait_write("color default")
        self.wait_write("top")
        self.wait_write("ip route 0.0.0.0 0.0.0.0 %s" % (self.transport_ipv4_gateway))
        self.wait_write("line vty 0 4")
        self.wait_write("transport input all")
        self.wait_write("line vty 5 10")
        self.wait_write("transport input ssh")
        self.wait_write("commit")
        self.wait_write("end", wait="#")
        self.logger.info("Completed bootstrap configuration")



class CSR(vrnetlab.VR):
    def __init__(self, username, password, **kwargs):
        super(CSR, self).__init__(username, password)
        self.vms = [ CSR_vm(username, password, **kwargs) ]


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
    parser.add_argument('--trace', default=vrnetlab.bool_from_env('TRACE'), action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default=os.getenv('USERNAME', 'vrnetlab'), help='Username')
    parser.add_argument('--password', default=os.getenv('PASSWORD', 'VR-netlab9'), help='Password')
    parser.add_argument('--install', default=vrnetlab.bool_from_env('INSTALL'), action='store_true', help='Install CSR')
    parser.add_argument('--organization-name', default=os.getenv('ORGANIZATION_NAME', 'SD-WAN CI'), help='Organization name')
    parser.add_argument('--sp-organization-name', default=os.getenv('SP_ORGANIZATION_NAME', 'SD-WAN CI'), help='SP organization name')
    parser.add_argument('--vbond', default=os.getenv('VBOND', '10.0.1.1'), help='vBond address')
    parser.add_argument('--system-ip', default=os.getenv('SYSTEM_IP', '10.1.1.100'), help='System IP address')
    parser.add_argument('--transport-ipv4-address', default=os.getenv('TRANSPORT_IPV4_ADDRESS', '10.1.1.1/24'), help='IPv4 address and prefix length on first transport interface')
    parser.add_argument('--transport-ipv4-gateway', default=os.getenv('TRANSPORT_IPV4_GATEWAY', '10.1.1.254'), help='IPv4 default gateway')
    parser.add_argument('--site-id', default=os.getenv('SITE_ID', 1), help='SD-WAN Site ID')

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
        vr = CSR(args.username, args.password,
               organization_name = args.organization_name,
               sp_organization_name = args.sp_organization_name,
               vbond = args.vbond,
               system_ip = args.system_ip,
               transport_ipv4_address = args.transport_ipv4_address,
               transport_ipv4_gateway = args.transport_ipv4_gateway,
               site_id = args.site_id)
        vr.start()
