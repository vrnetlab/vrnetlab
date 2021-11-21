#!/usr/bin/env python3

import datetime
import logging
import re
import signal
import subprocess
import sys
import time
import math
import os
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

class simulator_VM(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e

        self.ram = 16384
        self.vcpu = 6
        self.disk_size = '40G'
        super(simulator_VM, self).__init__(username, password, disk_image=disk_image, ram=self.ram)

        self.num_nics = 14
        self.wait_time = 30
        self.nic_type = 'virtio-net-pci'

        vrnetlab.run_command(["qemu-img", "create", "-f", "qcow2", "DataDisk.qcow2", self.disk_size])

        self.qemu_args.extend(["-smp", str(self.vcpu),
                               "-cpu", "host",
                               "-drive", "if=virtio,format=qcow2,file=DataDisk.qcow2"])

        self.qemu_args.extend(["-D", "/var/log/qemu.log"])

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        tn_switcher = {
            0: 'root',              # User Root Login
            1: 'Huawei@123',        # root password
            2: 'Root@123',          # time_client_start enter password
            3: 'Root@123',          # time_client_start enter again
            4: '\n'                   # Press Enter to Continue
        }

        (ridx, match, res) = self.tn.expect([b'localhost login: ',
                                             b'Password: ',
                                             b'Enter Password:',
                                             b'Confirm Password:',
                                             b'other key continue'], 1)

        if match:  # got a match!
            v = tn_switcher.get(ridx)
            self.wait_write(cmd=v, wait=None)
            # Enter the CLI, then config device
            if ridx == 3:
                # run main config!
                self.bootstrap_config()
                time.sleep(1)
                # send Ctrl + [ to close time_client_start
                # self.wait_write(cmd='\x1D', wait=None)
                # close telnet connection
                self.tn.close()
                # startup time?
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s" % startup_time)
                # mark as running
                self.running = True
                return

        time.sleep(5)

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

        self.wait_write(cmd="system-view", wait=">")
        self.wait_write(cmd="sysname HUAWEI", wait="]")
        self.wait_write(cmd="interface GigabitEthernet 0/0/0", wait="]")
        self.wait_write(cmd="ip address 10.0.0.15 24", wait="]")
        self.wait_write(cmd="commit", wait="]")

        # when simulator booting, config is not ok
        # Error: The system is busy in building configuration. Please wait for a moment...
        while True:
            (idx, match, res) = self.tn.expect([b'Error:'], 1)
            if match:
                if idx == 0:
                    self.wait_write(cmd="commit", wait=None)
                    time.sleep(5)
            else:
                break

        # add User vrnetlab
        self.wait_write(cmd="aaa", wait=None)
        self.wait_write(cmd="local-user %s password" % self.username, wait="]")
        self.wait_write(cmd="%s" % self.password, wait="Enter Password:")
        self.wait_write(cmd="%s" % self.password, wait="Confirm Password:")
        self.wait_write(cmd="local-user %s service-type ssh" % self.username, wait="]")
        self.wait_write(cmd="local-user %s user-group manage-ug" % self.username, wait="]")
        self.wait_write(cmd="commit", wait="]")


class simulator(vrnetlab.VR):

    def __init__(self, username, password):
         super(simulator, self).__init__(username, password)
         self.vms = [simulator_VM(username, password)]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    parser.add_argument('--num-nics', default=14, type=int, help='Number of NICs, this parameter is IGNORED, only added to be compatible with other platforms')

    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)

    if args.trace:
        logger.setLevel(1)

    vr = simulator(args.username, args.password)
    vr.start()
