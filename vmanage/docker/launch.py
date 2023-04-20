#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import sys
import telnetlib
import time
import requests

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

class VManage_vm(vrnetlab.VM):
    def __init__(self, username, password, **kwargs):
        disk_image = None
        for e in sorted(os.listdir("/")):
            if not disk_image and re.search(".qcow2$", e):
                disk_image = "/" + e

        self.disk_size = '100G'
        self.initial_config_done = False
        super(VManage_vm, self).__init__(username, password, disk_image=disk_image, ram=32768)
        self.organization_name = kwargs.get('organization_name')
        self.sp_organization_name = kwargs.get('sp_organization_name')
        self.vbond = kwargs.get('vbond')
        self.system_ip = kwargs.get('system_ip')
        self.transport_ipv4_address = kwargs.get('transport_ipv4_address')
        self.transport_ipv4_gateway = kwargs.get('transport_ipv4_gateway')
        self.site_id = kwargs.get('site_id')
        self.num_nics = 2
        self.qemu_args.extend(["-cpu", "host",
                               "-smp", "16"])
        vrnetlab.run_command(["qemu-img", "create", "-f", "qcow2", "DataDisk.qcow2", self.disk_size])
        self.qemu_args.extend(["-drive", "if=ide,format=qcow2,file=DataDisk.qcow2"])

    @property
    def admin_password(self):
        if self.initial_config_done:
            return "new-admin"
        else:
            return "admin"

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.logger.info("To many spins with no result, restarting")
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"System Ready"], 1)
        if match: # got a match!
            if ridx == 0: # System Ready
                self.logger.debug("Matched System Ready")
                # ConfD may not be fully operational in spite of seeing "System
                # Ready" on the device serial console. If we attempt to log in
                # and apply configuration, we may get an "application
                # communication error", which is a clear indicator of a
                # callpoint daemon not running, or the bootstrap process just
                # gets stuck ...
                self.logger.debug("Sleeping for 30s to let ConfD start everything up ...")
                time.sleep(30)
                self.wait_write("", wait=None)
                self.wait_write("admin", wait="vmanage login:")
                self.wait_write(self.admin_password, wait="Password:")
                self.logger.debug("Login completed")

                # perform initial config if necessary
                if not self.initial_config_done:
                    return self.initial_config()

                # perform bootstrap config
                self.bootstrap_config()

                # close telnet connection
                self.tn.close()
             
                # try to login to the API for up to 15 minutes
                for _ in range(450):
                    if self.api_login('localhost', 'admin', self.admin_password):
                        break
                    time.sleep(2)
                else:
                    self.logger.info("Too many attempts logging in to API, restarting ...")
                    self.stop()
                    self.start()
                    return

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

    def initial_config(self):
        """ Deal with a couple of setup questions after which
            the vManage reboots and is ready for use
        """
        self.logger.info("Applying initial configuration")
        # admin user password *must* be changed
        self.wait_write("new-admin", wait="Password:")
        self.wait_write("new-admin", wait="Re-enter password:")
        # vManage 20.6.1 introduced personas
        version_tuple = tuple(int(n) for n in self.version.split('.')[:3])
        if version_tuple >= (20, 6, 1):
            self.logger.info("Selecting Persona configuration")
            self.wait_write("1", wait="Select persona for vManage [1,2 or 3]:")
            self.wait_write("y", wait="Are you sure? [y/n]")
            self.wait_write("1", wait="Select storage device to use:")
            self.wait_write("y", wait="Would you like to format sdb? (y/n):")
            self.logger.info("Formating the SDB drive")
        else:
            self.wait_write("1", wait="Select storage device to use:")
            self.wait_write("y", wait="Would you like to format hdb? (y/n)")
        self.initial_config_done= True
        self.logger.info("Completed initial configuration")

    def bootstrap_config(self):
        """ Do the actual bootstrap config
        """
        self.logger.info("Applying bootstrap configuration")
        self.wait_write("config")
        self.wait_write("system aaa user %s" % (self.username))
        self.wait_write("password %s" % (self.password))
        self.wait_write("group netadmin")
        self.wait_write("top")
        self.wait_write("system system-ip %s" % (self.system_ip))
        self.wait_write("site-id %s" % (self.site_id))
        self.wait_write("organization-name \"%s\"" % (self.organization_name))
        self.wait_write("sp-organization-name \"%s\"" % (self.sp_organization_name))
        self.wait_write("vbond %s" % (self.vbond))
        self.wait_write("top")
        self.wait_write("no vpn 0 interface eth0")
        self.wait_write("vpn 512 interface eth0")
        self.wait_write("ip address 10.0.0.15/24")
        self.wait_write("no shutdown")
        self.wait_write("top")
        self.wait_write("vpn 0 interface eth1")
        self.wait_write("ip address %s" % (self.transport_ipv4_address))
        self.wait_write("tunnel-interface allow-service all")
        self.wait_write("exit")
        self.wait_write("no shutdown")
        self.wait_write("top")
        self.wait_write("vpn 0 ip route 0.0.0.0/0 %s" % (self.transport_ipv4_gateway))
        self.wait_write("commit and-quit")
        self.wait_write("end")
        self.logger.info("Completed bootstrap configuration")

    def api_login(self, vmanage_ip, username, password):
        """Login to vManage API"""
        session = requests.session()

        # URL for posting login data
        url = 'https://%s:443/j_security_check' % vmanage_ip

        # Format data for loginForm
        login_data = {
            'j_username' : username,
            'j_password' : password
        }

        try:
            response = session.post(url=url, data=login_data, verify=False, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            self.logger.trace(exc)
            return False

        if '<html>' in response.text:
            self.logger.trace("Login failed")
            return

        # Get token
        url = 'https://%s:443/dataservice/client/token' % vmanage_ip

        try:
            response = session.get(url=url, verify=False, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            self.logger.trace(exc)
            return False

        self.logger.info("Login succesful and client tokens available")
        return True


class VManage(vrnetlab.VR):
    def __init__(self, username, password, **kwargs):
        super(VManage, self).__init__(username, password)
        self.vms = [ VManage_vm(username, password, **kwargs) ]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', default=vrnetlab.bool_from_env('TRACE'), action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default=os.getenv('USERNAME', 'vrnetlab'), help='Username')
    parser.add_argument('--password', default=os.getenv('PASSWORD', 'VR-netlab9'), help='Password')
    parser.add_argument('--organization-name', default=os.getenv('ORGANIZATION_NAME', 'SD-WAN CI'), help='Organization name')
    parser.add_argument('--sp-organization-name', default=os.getenv('SP_ORGANIZATION_NAME', 'SD-WAN CI'), help='SP organization name')
    parser.add_argument('--vbond', default=os.getenv('VBOND', '10.0.1.1'), help='vBond address')
    parser.add_argument('--system-ip', default=os.getenv('SYSTEM_IP', '10.0.2.100'), help='System IP address')
    parser.add_argument('--transport-ipv4-address', default=os.getenv('TRANSPORT_IPV4_ADDRESS', '10.0.2.1/24'), help='IPv4 address and prefix length on first transport interface')
    parser.add_argument('--transport-ipv4-gateway', default=os.getenv('TRANSPORT_IPV4_GATEWAY', '10.0.2.254'), help='IPv4 default gateway')
    parser.add_argument('--site-id', default=os.getenv('SITE_ID', 100), help='SD-WAN Site ID')

    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = VManage(args.username, args.password,
               organization_name = args.organization_name,
               sp_organization_name = args.sp_organization_name,
               vbond = args.vbond,
               system_ip = args.system_ip,
               transport_ipv4_address = args.transport_ipv4_address,
               transport_ipv4_gateway = args.transport_ipv4_gateway,
               site_id = args.site_id)
    vr.start()
