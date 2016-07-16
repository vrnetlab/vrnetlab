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



class XRV:
    def __init__(self, username, password, num_id=None, ipv4_prefix=None, ipv6_prefix=None):
        self.spins = 0
        self.cycle = 0

        self.username = username
        self.password = password

        self.num_id = None
        self.ipv4_prefix = None
        self.ipv6_prefix = None
        self.mgmt_bridge = None

        self.ram = 4096
        self.num_nics = 20

        self.state = 0

        # basic argument sanity check
        if not (num_id or ipv4_prefix or ipv6_prefix):
            raise ValueError("num_id or ipv4_prefix or ipv6_prefix must be specified")

        # num_id sanity check
        if num_id:
            try:
                _ = int(num_id)
            except:
                raise TypeError("num_id must be a positive integer")
            if not num_id > 0:
                raise ValueError("num_id must be a positive integer")
            self.num_id = num_id

        # ipv4_prefix sanity check
        if ipv4_prefix:
            if _get_afi(ipv4_prefix) == 4:
                self.ipv4_prefix = ipv4_prefix
            else:
                raise ValueError("ipv4_prefix is not a valid IPv4 prefix, e.g. 192.0.2.1/24")

        # ipv6_prefix sanity check
        if ipv6_prefix:
            if _get_afi(ipv6_prefix) == 6:
                self.ipv6_prefix = ipv6_prefix
            else:
                raise ValueError("ipv6_prefix is not a valid IPv6 prefix, e.g. 2001:db8::1/64")

        # fill in defaults for ipv4_prefix and ipv6_prefix if they are not
        # explicitly specified
        if self.num_id:
            if not self.ipv4_prefix:
                self.ipv4_prefix = "10.0.0.%s/24" % self.num_id
            if not self.ipv6_prefix:
                self.ipv6_prefix = "2001:db8::%s/64" % self.num_id

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
               "-serial", "telnet:0.0.0.0:5000,server,nowait",
               "-hda", "/xrv.vmdk"
               ]

        # mgmt interface is always on a linux bridge!
        cmd.append("-device")
        cmd.append("e1000,netdev=vr%(num_id)02d_%(i)02d,mac=00:01:00:ff:%(num_id)s:%(i)02d"
                   % { 'num_id': self.num_id, 'i': 0 })
        cmd.append("-netdev")
        cmd.append("tap,ifname=vr%(num_id)02d_%(i)02d,id=vr%(num_id)s_%(i)02d,script=no,downscript=no"
                   % { 'num_id': self.num_id, 'i': 0 })

        for i in range(1, self.num_nics):
            cmd.append("-device")
            cmd.append("e1000,netdev=vr%(num_id)02d_%(i)02d,mac=00:01:00:ff:%(num_id)s:%(i)02d"
                       % { 'num_id': self.num_id, 'i': i })
            cmd.append("-netdev")
            #cmd.append("tap,ifname=vr%(num_id)02d_%(i)02d,id=vr%(num_id)s_%(i)02d,script=no,downscript=no"
            #           % { 'num_id': self.num_id, 'i': i })
            cmd.append("socket,id=vr%(num_id)s_%(i)02d,listen=:100%(i)02d"
                       % { 'num_id': self.num_id, 'i': i })

        run_command(cmd)
        # bring up all the NICs
        for i in range(0, self.num_nics):
            run_command(["ip", "link", "set", "vr%02d_%02d" % (self.num_id, i), "up"])


    def bootstrap_init(self):
        """ Do the initial part of the bootstrap process
        """
        self.tn = telnetlib.Telnet("127.0.0.1", 5000)
        

    def bootstrap_spin(self):
        """ This function should be called periodically to do work.

            It can be used when you don't want to block waiting for the router
            to boot, like when you are booting multiple routers in parallel.

            returns True, True      when it's done and succeeded
            returns True, False     when it's done but failed
            returns False, False    when there is still work to be done
        """

        if self.spins > 90:
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

        (ridx, match, res) = self.tn.expect([b"Press RETURN to get started",
            b"SYSTEM CONFIGURATION COMPLETE",
            b"Enter root-system username",
            b"Username:", b"^[^ ]+#"], 1)
        if match: # got a match!
            print("match", match, res)
            if ridx == 0: # press return to get started, so we press return!
                self.wait_write("", wait=None)
            if ridx == 1: # system configuration complete
                self.wait_write("", wait=None)
                self.state = 1
            if ridx == 2: # initial user config
                self.wait_write(self.username, wait=None)
                self.wait_write(self.password, wait="Enter secret:")
                self.wait_write(self.password, wait="Enter secret again:")
            if ridx == 3: # matched login prompt, so should login
                print("match login prompt")
                self.wait_write("admin", wait=None)
                self.wait_write("admin", wait="Password:")
            if self.state > 0 and ridx == 4:
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
        self.wait_write("", None)
        self.wait_write("crypto key generate rsa\r")
        if self.username and self.password:
            self.wait_write("admin")
            self.wait_write("configure")
            self.wait_write("username %s group root-system" % (self.username))
            self.wait_write("username %s group cisco-support" % (self.username))
            self.wait_write("username %s secret %s" % (self.username, self.password))
            self.wait_write("commit")
            self.wait_write("exit")
            self.wait_write("exit")
        self.wait_write("configure")
        # configure netconf
        self.wait_write("ssh server v2")
        self.wait_write("ssh server netconf port 830") # for 5.1.1
        self.wait_write("ssh server netconf vrf default") # for 5.3.3
        self.wait_write("netconf agent ssh") # for 5.1.1
        self.wait_write("netconf-yang agent ssh") # for 5.3.3

        # configure mgmt interface
        self.wait_write("interface MgmtEth 0/0/CPU0/0")
        self.wait_write("no shutdown")
        if self.ipv4_prefix:
            self.wait_write("ipv4 address %s" % self.ipv4_prefix)
        if self.ipv6_prefix:
            self.wait_write("ipv6 address %s" % self.ipv6_prefix)
        self.wait_write("exit")
        self.wait_write("commit")
        self.wait_write("exit")

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
    parser.add_argument('--ipv4-prefix', help='Management IPv4 prefix')
    parser.add_argument('--ipv6-prefix', help='Management IPv6 prefix')
    parser.add_argument('--username', help='Username')
    parser.add_argument('--password', help='Password')
    parser.add_argument('--mgmt-bridge', help='Linux bridge to attach mgmt interface too. Will be created if it does not already exist.')
    args = parser.parse_args()

    vr = XRV(args.username, args.password, args.numeric_id, args.ipv4_prefix, args.ipv6_prefix)
    vr.mgmt_bridge = args.mgmt_bridge
    vr.start()
    print("Going into sleep mode")
    while True:
        time.sleep(1)
