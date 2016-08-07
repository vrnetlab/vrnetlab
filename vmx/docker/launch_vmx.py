#!/usr/bin/env python3

import datetime
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


class VMX:
    def __init__(self, username, password):
        self.logger = logging.getLogger()
        self.spins = 0
        self.cycle = 0

        self.username = username
        self.password = password

        self.ram = 2048
        self.num_nics = None

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
        start_time = datetime.datetime.now()
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
        stop_time = datetime.datetime.now()
        self.logger.info("Startup complete in: %s" % (stop_time - start_time))


    def start_vm(self):
        """ Start the VM
        """
        self.logger.info("Starting VCP VM")
        # set up bridge for connecting VCP with vFPC
        run_command(["brctl", "addbr", "int_cp"])

        # start VCP VM (RE)
        cmd = ["qemu-system-x86_64", "-display", "none", "-daemonize", "-m", str(self.ram),
               "-serial", "telnet:0.0.0.0:5000,server,nowait",
               "-drive", "if=ide,file=/vmx/vmx.img",
               "-drive", "if=ide,file=/vmx/vmxhdd.img",
               "-smbios", "type=0,vendor=Juniper", "-smbios",
               "type=1,manufacturer=Juniper,product=VM-vcp_vmx2-161-re-0,version=0.1.0"
               ]
        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            cmd.insert(1, '-enable-kvm')

        # add metadata image if it exists
        if os.path.exists("/vmx/metadata-usb-re.img"):
            cmd.extend(["-usb", "-usbdevice", "disk:format=raw:/vmx/metadata-usb-re.img"])

        # mgmt interface is special - we use qemu user mode network
        cmd.append("-device")
        cmd.append("e1000,netdev=vcp0,mac=%s" % gen_mac(0))
        cmd.append("-netdev")
        cmd.append("user,id=vcp0,net=10.0.0.0/24,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=tcp::2830-10.0.0.15:830")
        # internal control plane interface to vFPC
        cmd.append("-device")
        cmd.append("virtio-net-pci,netdev=vcp-int,mac=%s" % gen_mac(1))
        cmd.append("-netdev")
        cmd.append("tap,ifname=vcp-int,id=vcp-int,script=no,downscript=no")

        run_command(cmd)

        # start VFP VM
        self.logger.info("Starting vFPC VM")
        cmd = ["kvm", "-display", "none", "-daemonize", "-m", "4096",
               "-cpu", "SandyBridge", "-M", "pc", "-smp", "3",
               "-serial", "telnet:0.0.0.0:5001,server,nowait",
               "-drive", "if=ide,file=/vmx/vfpc.img",
               ]
        # add metadata image if it exists
        if os.path.exists("/vmx/metadata-usb-fpc0.img"):
            cmd.extend(["-usb", "-usbdevice", "disk:format=raw:/vmx/metadata-usb-fpc0.img"])

        # mgmt interface is special - we use qemu user mode network
        cmd.extend(["-device", "virtio-net-pci,netdev=mgmt,mac=%s" % gen_mac(0)])
        cmd.extend(["-netdev", "user,id=mgmt,net=10.0.0.0/24"])
        # internal control plane interface to vFPC
        cmd.extend(["-device", "virtio-net-pci,netdev=vfpc-int,mac=%s" % gen_mac(0)])
        cmd.extend(["-netdev", "tap,ifname=vfpc-int,id=vfpc-int,script=no,downscript=no"])
        # dummy interface. not sure why vFPC wants it
        cmd.extend(["-device", "virtio-net-pci,netdev=dummy,mac=%s" % gen_mac(0)])
        cmd.extend(["-netdev", "tap,ifname=vfpc-dummy,id=dummy,script=no,downscript=no"])

        for i in range(1, self.num_nics):
            cmd.extend(["-device", "virtio-net-pci,netdev=p%(i)02d,mac=%(mac)s"
                       % { 'i': i, 'mac': gen_mac(i) }])
            cmd.extend(["-netdev", "socket,id=p%(i)02d,listen=:100%(i)02d"
                       % { 'i': i }])

        run_command(cmd)
        run_command(["brctl", "addif", "int_cp", "vcp-int"])
        run_command(["brctl", "addif", "int_cp", "vfpc-int"])
        run_command(["ip", "link", "set", "int_cp", "up"])
        run_command(["ip", "link", "set", "vcp-int", "up"])
        run_command(["ip", "link", "set", "vfpc-int", "up"])


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

        if self.spins > 300:
            # too many spins with no result
            if self.cycle == 0:
                # but if it's our first cycle we try to tickle the device to get a prompt
                self.wait_write("", wait=None)

                self.cycle += 1
                self.spins = 0
            else:
                # give up
                return True, False

        (ridx, match, res) = self.tn.expect([b"login:", b"root@(%|:~ #)"], 1)
        if match: # got a match!
            if ridx == 0: # matched login prompt, so should login
                self.logger.info("matched login prompt")
                self.wait_write("root", wait=None)
            if ridx == 1:
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
        self.wait_write("cli", None)
        self.wait_write("configure", '>', 10)
        self.wait_write("set chassis fpc 0 pic 0 number-of-ports %d" % self.num_nics)
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


    def wait_write(self, cmd, wait='#', timeout=None):
        """ Wait for something and then send command
        """
        if wait:
            self.logger.debug("Waiting for %s" % wait)
            while True:
                (ridx, match, res) = self.tn.expect([wait.encode(), b"Retry connection attempts"], timeout=timeout)
                if match:
                    if ridx == 0:
                        break
                    if ridx == 1:
                        self.tn.write("yes\r".encode())
            self.logger.debug("Read: %s" % res.decode())
        self.logger.debug("Running command: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    parser.add_argument('--num-nics', default=20, help='Number of interfaces')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = VMX(args.username, args.password)
    vr.num_nics = args.num_nics
    vr.start()
    logger.info("Going into sleep mode")
    while True:
        time.sleep(1)
