#!/usr/bin/env python3

import datetime
import logging
import os
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

class VSR_vm(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search(".qco$", e):
                disk_image = "/" + e
        super(VSR_vm, self).__init__(username, password, disk_image=disk_image, ram=1024)

        # The VSR supports up to 15 user nics
        self.num_nics = 7

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"Performing automatic"], 1)
        if match: # got a match!
            if ridx == 0: # login
                self.logger.debug("VM started")

                self.wait_write("", wait="(qemu)", con=self.qm)

                # To allow access to aux0 serial console
                self.logger.debug("Writing to QEMU Monitor")

                # Cred to @plajjan for this one
                commands = """\x04


system-view
user-interface aux 0
authentication-mode none
user-role network-admin
quit

"""

                key_map = {
                    '\x04': 'ctrl-d',
                    ' ': 'spc',
                    '-': 'minus',
                    '\n': 'kp_enter'
                }

                qemu_commands = [ "sendkey {}".format(key_map.get(c) or c) for c in commands ]

                for c in qemu_commands:
                    self.wait_write(c, wait="(qemu)", con=self.qm)
                    # Pace the characters sent via QEMU Monitor
                    time.sleep(0.1)

                self.logger.debug("Done writing to QEMU Monitor")
                self.logger.debug("Switching to line aux0")

                self.tn = telnetlib.Telnet("127.0.0.1", 5000 + self.num)

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
        self.wait_write("\r", None)
        # Wait for the prompt
        time.sleep(1)
        self.wait_write("system-view", "<HPE>")
        self.wait_write("ssh server enable", "[HPE]")
        self.wait_write("user-interface class vty", "[HPE]")
        self.wait_write("authentication-mode scheme", "[HPE-line-class-vty]")
        self.wait_write("protocol inbound ssh", "[HPE-line-class-vty]")
        self.wait_write("quit", "[HPE-line-class-vty]")
        self.wait_write("local-user %s" % (self.username), "[HPE]")
        self.wait_write("password simple %s" % (self.password), "[HPE-luser-manage-%s]" % (self.username))
        self.wait_write("service-type ssh", "[HPE-luser-manage-%s]" % (self.username))
        self.wait_write("authorization-attribute user-role network-admin", "[HPE-luser-manage-%s]" % (self.username))
        self.wait_write("quit", "[HPE-luser-manage-%s]" % (self.username))
        self.wait_write("interface GigabitEthernet%s/0" % (self.num_nics + 1), "[HPE]")
        self.wait_write("ip address 10.0.0.15 255.255.255.0", "[HPE-GigabitEthernet%s/0]" % (self.num_nics + 1))
        self.wait_write("quit", "[HPE-GigabitEthernet%s/0]" % (self.num_nics + 1))
        self.wait_write("quit", "[HPE]")
        self.wait_write("quit", "<HPE>")
        self.logger.info("completed bootstrap configuration")

class VSR(vrnetlab.VR):
    def __init__(self, username, password):
        super(VSR, self).__init__(username, password)
        self.vms = [ VSR_vm(username, password) ]

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

    vr = VSR(args.username, args.password)
    vr.start()
