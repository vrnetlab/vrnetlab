#!/usr/bin/env python3

import re
import signal
import sys
import telnetlib
import time

import IPy


def signal_handler(signal, frame):
    print('Shutting down...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_command(cmd, cwd=None):
    import subprocess
    res = None
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd)
        res = p.communicate()
    except:
        pass
    return res

def _is_ipv4(ip):
    """ Return true if given arg is a valid IPv4 address
    """
    try:
        p = IPy.IP(ip)
    except ValueError:
        return False

    if p.version() == 4:
        return True
    return False

def _is_ipv6(ip):
    """ Return true if given arg is a valid IPv6 address
    """
    try:
        p = IPy.IP(ip)
    except ValueError:
        return False

    if p.version() == 6:
        return True
    return False

def _get_afi(ip):
    """ Return address-family (4 or 6) for IP or None if invalid address
    """

    parts = unicode(ip).split("/")
    if len(parts) == 1:
        # just an address
        if _is_ipv4(ip):
            return 4
        elif _is_ipv6(ip):
            return 6
        else:
            return None
    elif len(parts) == 2:
        # a prefix!
        try:
            pl = int(parts[1])
        except ValueError:
            # if casting parts[1] to int failes, this is not a prefix..
            return None

        if _is_ipv4(parts[0]):
            if pl >= 0 and pl <= 32:
                # prefix mask must be between 0 and 32
                return 4
            # otherwise error
            return None
        elif _is_ipv6(parts[0]):
            if pl >= 0 and pl <= 128:
                # prefix mask must be between 0 and 128
                return 6
            # otherwise error
            return None
        else:
            return None
    else:
        # more than two parts.. this is neither an address or a prefix
        return None



class InitAlu:
    def __init__(self, username, password, num_id=None):
        self.spins = 0
        self.cycle = 0

        self.username = username
        self.password = password

        self.num_id = None
        self.mgmt_bridge = None

        self.ram = 4096
        self.num_nics = 20

        # num_id sanity check
        if num_id:
            try:
                _ = int(num_id)
            except:
                raise TypeError("num_id must be a positive integer")
            if not num_id > 0:
                raise ValueError("num_id must be a positive integer")
            self.num_id = num_id

        self.num_id = num_id


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
        self.start_vm()
        if self.mgmt_bridge:
            print("Configuring mgmt-bridge")
            run_command(["brctl", "addbr", self.mgmt_bridge])
            run_command(["brctl", "addif", self.mgmt_bridge, "vr%02d_00" % self.num_id])
            run_command(["ip", "link", "set", self.mgmt_bridge, "up"])
        self.bootstrap_init()
        if blocking:
            while True:
                done, res = self.bootstrap_spin()
                if done:
                    break
            self.bootstrap_end()


    def start_vm(self):
        """ Start the VM
        """
        cmd = ["kvm", "-display", "none", "-daemonize", "-m", str(self.ram),
               "-serial", "telnet:127.0.0.1:10%02d,server,nowait" % self.num_id, "-smbios",
               "type=1,product=TIMOS:slot=A chassis=SR-c12 card=cfm-xp-b mda/1=m20-1gb-xp-sfp mda/3=m20-1gb-xp-sfp mda/5=m20-1gb-xp-sfp",
               "-hda", "/sros.qcow2"
               ]

        for i in range(0, self.num_nics):
            cmd.append("-device")
            cmd.append("e1000,netdev=vr%(num_id)02d_%(i)02d,mac=00:01:00:ff:%(num_id)s:%(i)02d"
                       % { 'num_id': self.num_id, 'i': i })
            cmd.append("-netdev")
            cmd.append("tap,ifname=vr%(num_id)02d_%(i)02d,id=vr%(num_id)s_%(i)02d,script=no,downscript=no"
                       % { 'num_id': self.num_id, 'i': i })

        run_command(cmd)
        # bring up all the NICs
        for i in range(0, self.num_nics):
            run_command(["ip", "link", "set", "vr%02d_%02d" % (self.num_id, i), "up"])


    def bootstrap_init(self):
        """ Do the initial part of the bootstrap process
        """
        self.tn = telnetlib.Telnet("127.0.0.1", int("10%d" % self.num_id))
        
    def bootstrap_spin(self):
        """ This function should be called periodically to do work.

            It can be used when you don't want to block waiting for the router
            to boot, like when you are booting multiple routers in parallel.

            returns True, True      when it's done and succeeded
            returns True, False     when it's done but failed
            returns False, False    when there is still work to be done
        """

        if self.spins > 30:
            # too many spins with no result
            if self.cycle == 0:
                # but if it's our first cycle we try to tickle the device to get a prompt
                self.wait_write("", wait=None)

                self.cycle += 1
                self.spins = 0
            else:
                # give up
                return True, False


        print(".")
        (ridx, match, res) = self.tn.expect([b"Login:", b"^[^ ]+#"], 1)
        if match: # got a match!
            print("match")
            if ridx == 0: # matched login prompt, so should login
                print("match login prompt")
                self.wait_write("admin", wait=None)
                self.wait_write("admin", wait="Password:")
            # run main config!
            self.bootstrap_config()
            return True, True

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b'':
            print("OUTPUT:", res)
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return False, False


    def bootstrap_config(self):
        """ Do the actual bootstrap config
        """
        self.wait_write("bof address 10.0.0.15/24")
        self.wait_write(b"bof save")
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


    def wait_write(self, cmd, wait='#'):
        """ Wait for something and then send command
        """
        if wait:
            print("Waiting for %s" % wait)
            res = self.tn.read_until(wait.encode())
            print("Read:", res)
        print("Running command: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--numeric-id', type=int, help='Numeric ID')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='vrnetlab', help='Password')
    parser.add_argument('--mgmt-bridge', help='Linux bridge to attach mgmt interface too. Will be created if it does not already exist.')
    args = parser.parse_args()

    ia = InitAlu(args.username, args.password, args.numeric_id)
    ia.mgmt_bridge = args.mgmt_bridge
    ia.start()
    print("Going into sleep mode")
    while True:
        time.sleep(1)
