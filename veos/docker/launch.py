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

import IPy

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

def run_command(cmd, cwd=None, background=False):
    import subprocess
    res = None
    try:
        if background:
            p = subprocess.Popen(cmd, cwd=cwd)
        else:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd)
            res = p.communicate()
    except:
        pass
    return res

def gen_mac(last_octet=None):
    """ Generate a random MAC address that is in the qemu OUI space and that
        has the given last octet.
    """
    return "52:54:00:%02x:%02x:%02x" % (
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            last_octet
        )


class VEOS:
    def __init__(self, username, password):
        self.logger = logging.getLogger()
        self.spins = 0

        self.username = username
        self.password = password

        self.ram = 2048
        self.num_nics = 20

        self.boot_iso = None
        self.image = None
        # control plane started?
        self.cp_started = False


    def start(self):
        """ Start the virtual router

            This can take a long time as we are waiting for the router to start
            and the do initial bootstraping of it over serial port.
        """
        start_time = datetime.datetime.now()
        self.start_vm()
        run_command(["socat", "TCP-LISTEN:22,fork", "TCP:127.0.0.1:2022"], background=True)
        run_command(["socat", "TCP-LISTEN:830,fork", "TCP:127.0.0.1:2830"], background=True)
        self.bootstrap_init()
        while not (self.cp_started):
            if not self.bootstrap_spin():
                break
        self.bootstrap_end()
        stop_time = datetime.datetime.now()
        self.logger.info("Startup complete in: %s" % (stop_time - start_time))



    def start_vm(self):
        """ Start the VM
        """
        for e in os.listdir("/"):
            if re.search("\.vmdk$", e):
                self.image = "/" + e
            if re.search("\.iso$", e):
                self.boot_iso = "/" + e

        self.logger.info("Starting VM")

        cmd = ["qemu-system-x86_64", "-display", "none", "-daemonize", "-m", str(self.ram),
               "-serial", "telnet:0.0.0.0:5000,server,nowait",
               "-cdrom", self.boot_iso, "-boot", "d", "-hda", self.image
               ]
        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            cmd.insert(1, '-enable-kvm')

        # mgmt interface is special - we use qemu user mode network
        cmd.append("-device")
        cmd.append("e1000,netdev=p%(i)02d,mac=%(mac)s"
                   % { 'i': 0, 'mac': gen_mac(0) })
        cmd.append("-netdev")
        cmd.append("user,id=p%(i)02d,net=10.0.0.0/24,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=tcp::2830-10.0.0.15:830"
                   % { 'i': 0 })

        for i in range(1, self.num_nics):
            cmd.append("-device")
            cmd.append("e1000,netdev=p%(i)02d,mac=%(mac)s"
                       % { 'i': i, 'mac': gen_mac(i) })
            cmd.append("-netdev")
            cmd.append("socket,id=p%(i)02d,listen=:100%(i)02d"
                       % { 'i': i })

        run_command(cmd)


    def bootstrap_init(self):
        """ Do the initial part of the bootstrap process
        """
        self.tn = telnetlib.Telnet("127.0.0.1", 5000)
        

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.
        """

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.logger.error("startup took too long - giving up")
            return False

        (ridx, match, res) = self.tn.expect([b"login:"], 1)
        if match: # got a match!
            if ridx == 0: # login
                self.logger.debug("matched login prompt")
                self.logger.debug("trying to log in with 'admin'")
                self.wait_write("admin", wait=None)

                # run main config!
                self.bootstrap_config()
                self.cp_started = True

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b'':
            self.logger.trace("OUTPUT: %s" % res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return True


    def bootstrap_config(self):
        """ Do the actual bootstrap config
        """
        self.logger.info("applying bootstrap configuration")
        self.wait_write("", None)
        self.wait_write("enable", ">")
        self.wait_write("configure")
        self.wait_write("username %s secret 0 %s role network-admin" % (self.username, self.password))

        # configure mgmt interface
        self.wait_write("interface Management 1")
        self.wait_write("ip address 10.0.0.15/24")
        self.wait_write("exit")
        self.wait_write("exit")
        self.wait_write("copy running-config startup-config")

    def bootstrap_end(self):
        self.tn.close()


    def wait_write(self, cmd, wait='#'):
        """ Wait for something and then send command
        """
        if wait:
            self.logger.trace("waiting for '%s' on serial console" % wait)
            res = self.tn.read_until(wait.encode())
            self.logger.trace("read from serial console: %s" % res.decode())
        self.logger.debug("writing to serial console: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())



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

    vr = VEOS(args.username, args.password)
    vr.start()
    logger.info("Going into sleep mode")
    while True:
        time.sleep(1)
