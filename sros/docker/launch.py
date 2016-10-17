#!/usr/bin/env python3

import datetime
import logging
import os
import random
import re
import signal
import subprocess
import sys
import telnetlib
import time

import IPy

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


def mangle_uuid(uuid):
    """ Mangle the UUID to fix endianness mismatch on first part
    """
    parts = uuid.split("-")

    new_parts = [
        uuid_rev_part(parts[0]),
        uuid_rev_part(parts[1]),
        uuid_rev_part(parts[2]),
        parts[3],
        parts[4]
    ]

    return '-'.join(new_parts)


def uuid_rev_part(part):
    """ Reverse part of a UUID
    """
    res = ""
    for i in reversed(range(0, len(part), 2)):
        res += part[i]
        res += part[i+1]
    return res




class SROS_vm(vrnetlab.VM):
    def __init__(self, username, password):
        super(SROS_vm, self).__init__(username, password, disk_image = "/sros.qcow2")
        self.num_nics = 20

        # move files into place
        for e in os.listdir("/"):
            if re.search("\.qcow2$", e):
                os.rename("/" + e, "/sros.qcow2")
            if re.search("\.license$", e):
                os.rename("/" + e, "/tftpboot/license.txt")

        self.uuid = "00000000-0000-0000-0000-000000000000"

        self.read_license()
        self.smbios = ["type=1,product=TIMOS:address=10.0.0.15/24@active license-file=tftp://10.0.0.2/license.txt slot=A chassis=SR-c12 card=cfm-xp-b mda/1=m20-1gb-xp-sfp mda/3=m20-1gb-xp-sfp mda/5=m20-1gb-xp-sfp"]



    def gen_mgmt(self):
        """ Generate mgmt interface(s)

            We override the default function since we want a fake NIC in there
        """
        # call parent function to generate first mgmt interface (e1000)
        res = super(SROS_vm, self).gen_mgmt()
        # add virtio NIC for internal control plane interface to vFPC
        res.append("-device")
        res.append("e1000,netdev=dummy0,mac=%s" % vrnetlab.gen_mac(1))
        res.append("-netdev")
        res.append("tap,ifname=dummy0,id=dummy0,script=no,downscript=no")
        return res




    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 60:
            # too many spins with no result, probably means SROS hasn't started
            # successfully, so we restart it
            self.logger.warning("no output from serial console, restarting VM")
            self.stop_vm()
            self.start_vm()
            self.spins = 0
            return

        (ridx, match, res) = self.tn.expect([b"Login:", b"^[^ ]+#"], 1)
        if match: # got a match!
            if ridx == 0: # matched login prompt, so should login
                self.logger.debug("matched login prompt")
                self.wait_write("admin", wait=None)
                self.wait_write("admin", wait="Password:")
            # run main config!
            self.bootstrap_config()
            # close telnet connection
            self.tn.close()
            # calc startup time
            startup_time = datetime.datetime.now() - self.start_time
            self.logger.info("Startup complete in: %s" % startup_time)
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
        if self.username and self.password:
            self.wait_write("configure system security user \"%s\" password %s" % (self.username, self.password))
            self.wait_write("configure system security user \"%s\" access console netconf" % (self.username))
            self.wait_write("configure system security user \"%s\" console member \"administrative\" \"default\"" % (self.username))
        self.wait_write("configure system netconf no shutdown")
        self.wait_write("configure card 1 mda 1 shutdown")
        self.wait_write("configure card 1 mda 1 no mda-type")
        self.wait_write("configure card 1 shutdown")
        self.wait_write("configure card 1 no card-type")
        self.wait_write("configure card 1 card-type iom-xp-b")
        self.wait_write("configure card 1 mcm 1 mcm-type mcm-xp")
        self.wait_write("configure card 1 mcm 3 mcm-type mcm-xp")
        self.wait_write("configure card 1 mcm 5 mcm-type mcm-xp")
        self.wait_write("configure card 1 mda 1 mda-type m20-1gb-xp-sfp")
        self.wait_write("configure card 1 mda 3 mda-type m20-1gb-xp-sfp")
        self.wait_write("configure card 1 mda 5 mda-type m20-1gb-xp-sfp")
        self.wait_write("configure card 1 no shutdown")
        self.wait_write("admin save")
        self.wait_write("logout")



    def read_license(self):
        """ Read the license file, if it exists, and extract the UUID and start
            time of the license
        """
        if not os.path.isfile("/tftpboot/license.txt"):
            self.logger.info("No license file found")
            return

        lic_file = open("/tftpboot/license.txt", "r")
        license = lic_file.read()
        lic_file.close()
        try:
            uuid_input = license.split(" ")[0]
            self.uuid = mangle_uuid(uuid_input)
            m = re.search("([0-9]{4}-[0-9]{2}-)([0-9]{2})", license)
            if m:
                self.fake_start_date = "%s%02d" % (m.group(1), int(m.group(2))+1)
        except:
            raise ValueError("Unable to parse license file")
        self.logger.info("License file found for UUID %s with start date %s" % (self.uuid, self.fake_start_date))




class SROS(vrnetlab.VR):
    def __init__(self, username, password):
        super(SROS, self).__init__(username, password)

        self.vms = [ SROS_vm(username, password) ]



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

    ia = SROS(args.username, args.password)
    ia.start()
