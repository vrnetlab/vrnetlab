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

def run_command(cmd, cwd=None, background=False):
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


class SROS(vrnetlab.VR):
    def __init__(self):
        self.logger = logging.getLogger()
        self.spins = 0

        self.username = None
        self.password = None

        self.ram = 4096
        self.num_nics = 20

        self.uuid = "00000000-0000-0000-0000-000000000000"
        self.license_start = None



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
                self.license_start = "%s%02d" % (m.group(1), int(m.group(2))+1)
        except:
            raise ValueError("Unable to parse license file")
        self.logger.info("License file found for UUID %s with start date %s" % (self.uuid, self.license_start))



    def start(self, blocking=True):
        """ Start the virtual router

            This can take a long time as we are waiting for the router to start
            and the do initial bootstraping of it over serial port. It is
            possible to set blocking=False which means only the first parts of
            the startup process are run. You are expected to call the
            bootstrap_spin() function periodically (like once a second) after
            this to complete the bootstrap process. Once bootstrap_spin()
            returns True you are done!
        """
        self.update_health(2, "SROS starting")
        start_time = datetime.datetime.now()
        self.start_vm()
        run_command(["socat", "TCP-LISTEN:22,fork", "TCP:127.0.0.1:2022"], background=True)
        run_command(["socat", "TCP-LISTEN:830,fork", "TCP:127.0.0.1:2830"], background=True)
        if blocking:
            while True:
                done, res = self.bootstrap_spin()
                if done:
                    break
            self.bootstrap_end()
        stop_time = datetime.datetime.now()
        self.logger.info("Startup complete in: %s" % (stop_time - start_time))


    def start_vm(self):
        """ Start the VM
        """
        # move files into place
        for e in os.listdir("/"):
            if re.search("\.qcow2$", e):
                os.rename("/" + e, "/sros.qcow2")
            if re.search("\.license$", e):
                os.mkdir("/tftpboot")
                os.rename("/" + e, "/tftpboot/license.txt")
        self.read_license()

        self.logger.info("Starting VM")
        bof = "type=1,product=TIMOS:address=10.0.0.15/24@active license-file=tftp://10.0.0.2/license.txt slot=A chassis=SR-c12 card=cfm-xp-b mda/1=m20-1gb-xp-sfp mda/3=m20-1gb-xp-sfp mda/5=m20-1gb-xp-sfp"

        cmd = ["qemu-system-x86_64", "-display", "none", "-m", str(self.ram),
               "-serial", "telnet:0.0.0.0:5000,server,nowait", "-smbios", bof,
               "-hda", "/sros.qcow2", "-uuid", self.uuid
               ]
        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            cmd.insert(1, '-enable-kvm')

        # do we have a license start date?
        if self.license_start:
            cmd.extend(["-rtc", "base=" + self.license_start])

        # mgmt interface is special - we use qemu user mode network
        cmd.append("-device")
        cmd.append("e1000,netdev=mgmt,mac=%(mac)s"
                   % { 'mac': gen_mac(0) })
        cmd.append("-netdev")
        cmd.append("user,id=mgmt,net=10.0.0.0/24,tftp=/tftpboot,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=tcp::2830-10.0.0.15:830")
        # dummy interface
        cmd.extend(["-device", "e1000,netdev=dummy,mac=%s" % gen_mac(0)])
        cmd.extend(["-netdev", "tap,ifname=vfpc-dummy,id=dummy,script=no,downscript=no"])

        for i in range(1, self.num_nics):
            cmd.append("-device")
            cmd.append("e1000,netdev=p%(i)02d,mac=%(mac)s"
                       % { 'i': i, 'mac': gen_mac(i) })
            cmd.append("-netdev")
            cmd.append("socket,id=p%(i)02d,listen=:100%(i)02d"
                       % { 'i': i })

        self.p_vm = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        try:
            self.p_vm.communicate('', 1)
        except:
            pass

        self.tn = telnetlib.Telnet("127.0.0.1", 5000)


    def stop_vm(self):
        try:
            self.p_vm.terminate()
        except ProcessLookupError:
            return

        try:
            self.p_vm.communicate(timeout=10)
        except:
            self.p_vm.kill()
            self.p_vm.communicate(timeout=10)



    def bootstrap_spin(self):
        """ This function should be called periodically to do work.

            It can be used when you don't want to block waiting for the router
            to boot, like when you are booting multiple routers in parallel.

            returns True, True      when it's done and succeeded
            returns True, False     when it's done but failed
            returns False, False    when there is still work to be done
        """

        if self.spins > 60:
            # too many spins with no result, probably means SROS hasn't started
            # successfully, so we restart it
            self.logger.warning("no output from serial console, restarting VM")
            self.stop_vm()
            self.start_vm()
            self.spins = 0
            return False, False

        (ridx, match, res) = self.tn.expect([b"Login:", b"^[^ ]+#"], 1)
        if match: # got a match!
            if ridx == 0: # matched login prompt, so should login
                self.logger.debug("matched login prompt")
                self.wait_write("admin", wait=None)
                self.wait_write("admin", wait="Password:")
            # run main config!
            self.bootstrap_config()
            return True, True

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b'':
            self.logger.trace("OUTPUT: %s" % res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return False, False


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


    def bootstrap_end(self):
        self.tn.close()
        self.update_health(0, "SROS started")


    def wait_write(self, cmd, wait='#'):
        """ Wait for something and then send command
        """
        if wait:
            self.logger.trace("Waiting for %s" % wait)
            res = self.tn.read_until(wait.encode())
            self.logger.trace("Read: %s" % res.decode())
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

    ia = SROS()
    ia.username = args.username
    ia.password = args.password
    ia.start()
    logger.info("Going into sleep mode")
    while True:
        time.sleep(1)
