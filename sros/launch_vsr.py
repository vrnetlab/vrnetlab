#!/usr/bin/env python3

import os
import random
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

def gen_mac(last_octet=None):
    """ Generate a random MAC address that is in the qemu OUI space and that
        has the given last octet.
    """
    return "52:54:00:%02x:%02x:%02x" % (
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            last_octet
        )


class InitAlu:
    def __init__(self, username, password):
        self.spins = 0
        self.cycle = 0

        self.username = username
        self.password = password

        self.ram = 4096
        self.num_nics = 20


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
        run_command(["socat", "TCP-LISTEN:22,fork", "TCP:127.0.0.1:2022"], background=True)
        run_command(["socat", "TCP-LISTEN:830,fork", "TCP:127.0.0.1:2830"], background=True)
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
        cmd = ["qemu-system-x86_64", "-display", "none", "-daemonize", "-m", str(self.ram),
               "-serial", "telnet:0.0.0.0:5000,server,nowait", "-smbios",
               "type=1,product=TIMOS:slot=A chassis=SR-c12 card=cfm-xp-b mda/1=m20-1gb-xp-sfp mda/3=m20-1gb-xp-sfp mda/5=m20-1gb-xp-sfp",
               "-hda", "/sros.qcow2"
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
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    args = parser.parse_args()

    ia = InitAlu(args.username, args.password)
    ia.start()
    print("Going into sleep mode")
    while True:
        time.sleep(1)
