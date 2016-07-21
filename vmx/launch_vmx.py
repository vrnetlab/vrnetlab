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


class VMX:
    def __init__(self, username, password):
        self.spins = 0
        self.cycle = 0

        self.username = username
        self.password = password

        self.ram = 4096
        self.num_nics = 20

        self.state = 0


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
        # set up bridge for connecting VCP with vFPC
        run_command(["brctl", "addbr", "int_cp"])

        # start VCP VM (RE)
        cmd = ["qemu-system-x86_64", "-display", "none", "-daemonize", "-m", str(self.ram),
               "-serial", "telnet:0.0.0.0:5000,server,nowait",
               "-drive", "if=ide,file=/vmx/jinstall64-vmx.img",
               "-drive", "if=ide,file=/vmx/vmxhdd.img",
               "-smbios", "type=0,vendor=Juniper", "-smbios",
               "type=1,manufacturer=Juniper,product=VM-vcp_vmx2-161-re-0,version=0.1.0",
               "-usb", "-usbdevice", "disk:format=raw:/vmx/metadata_usb.img"
               ]
        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            cmd.insert(1, '-enable-kvm')

        # mgmt interface is special - we use qemu user mode network
        cmd.append("-device")
        cmd.append("virtio-net-pci,netdev=vcp0,mac=%s" % gen_mac(0))
        cmd.append("-netdev")
        cmd.append("user,id=vcp0,net=10.0.0.0/24,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=tcp::2830-10.0.0.15:830")
        # internal control plane interface to vFPC
        cmd.append("-device")
        cmd.append("virtio-net-pci,netdev=vcp1,mac=%s" % gen_mac(1))
        cmd.append("-netdev")
        cmd.append("tap,ifname=vcp1,id=vcp1,script=no,downscript=no")

        run_command(cmd)

        # start VFP VM
        cmd = ["kvm", "-display", "none", "-daemonize", "-m", str(self.ram),
               "-cpu", "SandyBridge", "-M", "pc", "-smp", "4",
               "-serial", "telnet:0.0.0.0:5001,server,nowait",
               "-drive", "if=ide,file=/vmx/vfpc.img",
               ]

        # mgmt interface is special - we use qemu user mode network
        cmd.extend(["-device", "virtio-net-pci,netdev=vfpc0,mac=%s" % gen_mac(0)])
        cmd.extend(["-netdev", "user,id=vfpc0,net=10.0.0.0/24"])
        # internal control plane interface to vFPC
        cmd.extend(["-device", "virtio-net-pci,netdev=vfpc1,mac=%s" % gen_mac(0)])
        cmd.extend(["-netdev", "tap,ifname=vfpc1,id=vfpc1,script=no,downscript=no"])

        for i in range(1, self.num_nics):
            cmd.extend(["-device", "virtio-net-pci,netdev=p%(i)02d,mac=%(mac)s"
                       % { 'i': i, 'mac': gen_mac(i) }])
            cmd.extend(["-netdev", "socket,id=p%(i)02d,listen=:100%(i)02d"
                       % { 'i': i }])

        run_command(cmd)
        run_command(["brctl", "addif", "int_cp", "vcp1"])
        run_command(["brctl", "addif", "int_cp", "vfpc1"])
        run_command(["ip", "link", "set", "int_cp", "up"])
        run_command(["ip", "link", "set", "vcp1", "up"])
        run_command(["ip", "link", "set", "vfpc1", "up"])


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

        if self.spins > 120:
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

        (ridx, match, res) = self.tn.expect([b"login:", b"^[^ ]+%"], 1)
        if match: # got a match!
            print("match", match, res)
            if ridx == 0: # matched login prompt, so should login
                print("match login prompt")
                self.wait_write("root", wait=None)
            if ridx == 1:
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
        self.wait_write("cli", None)
        self.wait_write("configure", '>')
        self.wait_write("set system services ssh")
        self.wait_write("set system services netconf ssh")
        self.wait_write("set system services netconf rfc-compliant")
        self.wait_write("set system login user %s class super-user authentication plain-text-password" % self.username)
        self.wait_write(self.password, 'New password:')
        self.wait_write(self.password, 'Retype new password:')
        self.wait_write("set system root-authentication plain-text-password")
        self.wait_write(self.password, 'New password:')
        self.wait_write(self.password, 'Retype new password:')
        self.wait_write("set interfaces fxp0 unit 0 family inet address 10.0.0.15/24")
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
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    args = parser.parse_args()

    vr = VMX(args.username, args.password)
    vr.start()
    print("Going into sleep mode")
    while True:
        time.sleep(1)
