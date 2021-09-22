#!/usr/bin/env python3

import argparse
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



class NXOS9K_vm(vrnetlab.VM):
    def __init__(self, bios, username, password, num_nics):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        # the parent constructor needs to call create_overlay_image,
        # so must initialize the other parameters first
        self.bios = bios
        self.prompted = False
        self.overlay_image = None
        super().__init__(username, password, disk_image=disk_image, ram=8192)
        self.num_nics = num_nics
        self.credentials = [
                ['admin', 'Cisco1234']
            ]


    def create_overlay_image(self):
        self.overlay_image = re.sub(r'(\.[^.]+$)', r'-overlay\1', self.image)
        extended_args = ['-nographic', '-bios', self.bios, '-smp', '2']
        # remove previously old overlay image, otherwise boot fails
        if os.path.exists(self.overlay_image):
            os.remove(self.overlay_image)
        # now re-create it!
        super().create_overlay_image()
        # use SATA driver for disk and set to drive 0
        extended_args.extend(['-device', 'ahci,id=ahci0,bus=pci.0',
            '-drive', 'if=none,file=%s,id=drive-sata-disk0,format=qcow2' % self.overlay_image,
            '-device', 'ide-drive,bus=ahci0.0,drive=drive-sata-disk0,id=drive-sata-disk0'])
        # create initial config and load it
        vrnetlab.run_command(['genisoimage', '-o', '/cfg.iso', '-l', '--iso-level', '2', 'nxos_config.txt'])
        extended_args.extend(['-drive', 'file=cfg.iso,media=cdrom'])


        return extended_args

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        # press return to get prompt every 10 seconds
        if not self.prompted and self.spins % 10 == 0:
            self.wait_write('', wait=None)
        if self.spins > 300:
            # too many spins with no result ->  give up
            self.prompted = False
            self.stop()
            # re-create overlay image
            self.create_overlay_image()
            self.start()
            return

        username, password = self.credentials[0]
        (ridx, match, res) = self.tn.expect([b'login:', b'Enter the password for "admin":', b'Confirm the password for "admin":'], 1)
        if match: # got a match!
            self.prompted = True
            self.logger.info("match found: %s", res.decode())
            if ridx == 0: # login
                self.logger.info("matched login prompt")
                self.logger.info("trying to log in with %s / %s", username, password)
                self.wait_write(username, wait=None)
                self.wait_write(password, wait="Password:")

                # run main config!
                self.bootstrap_config()
                # close telnet connection
                self.tn.close()
                # startup time?
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s", startup_time)
                # mark as running
                self.running = True
            else:
                self.logger.info("Trying to reset admin password to %s", password)
                self.wait_write(password, wait=None)
                self.wait_write(password, wait='password')

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        elif res != b'':
            self.logger.trace("OUTPUT: %s", res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return


    def bootstrap_config(self):
        """ Do the actual bootstrap config
        """
        self.logger.info("applying bootstrap configuration")
        self.wait_write("", None)
        # figure out the running image
        self.wait_write("", None)
        self.wait_write("configure")
        self.wait_write("username %s password 0 %s role network-admin" % (self.username, self.password))

        # configure mgmt interface
        self.wait_write("interface mgmt0")
        self.wait_write("ip address 10.0.0.15/24")
        self.wait_write("exit")
        # enable netconf with 10 sessions (max allowed)
        self.wait_write("feature netconf")
        self.wait_write("netconf sessions 10")
        self.wait_write("exit")
        self.wait_write("copy running-config startup-config")


class NXOS9K(vrnetlab.VR):
    def __init__(self, bios, username, password, num_nics):
        super().__init__(username, password)
        self.vms = [ NXOS9K_vm(bios, username, password, num_nics) ]

def main():
    """Main method"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    parser.add_argument('--bios', default='OVMF-pure-efi.fd', help='EFI bios image')
    parser.add_argument('--num-nics', type=int, default=24, help='Number of NICs')
    args = parser.parse_args()

    # check if the bios file exists
    if not os.path.exists(args.bios):
        print('Bios file %s does not exit' % args.bios)
        sys.exit(1)

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = NXOS9K(args.bios, args.username, args.password, args.num_nics)
    vr.start()

if __name__ == '__main__':
    main()
