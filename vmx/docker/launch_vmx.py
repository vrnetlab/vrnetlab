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


class VMX:
    def __init__(self, username, password):
        self.logger = logging.getLogger()
        self.vcp_started = False
        self.vfpc_started = False
        self.tn_vcp = None
        self.tn_vfpc = None
        self.spins = 0

        self.username = username
        self.password = password

        self.ram = 2048
        self.num_nics = None

        self.vcp_image = None


    def read_version(self):
        for e in os.listdir("/vmx/"):
            m = re.search("-(([0-9][0-9])\.([0-9])([A-Z])([0-9])\.([0-9]))\.qcow2$", e)
            if m:
                self.image = "/vmx/" + e
                self.version = m.group(1)
                self.version_info = [int(m.group(2)), int(m.group(3)), m.group(4), int(m.group(5)), int(m.group(6))]


    def start(self):
        """ Start the virtual router

            This can take a long time as we are waiting for the router to start
            and the do initial bootstraping of it over serial port.
        """
        self.read_version()
        self.logger.info("Starting vMX %s" % self.version)

        start_time = datetime.datetime.now()
        # set up bridge for connecting VCP with vFPC
        run_command(["brctl", "addbr", "int_cp"])
        run_command(["ip", "link", "set", "int_cp", "up"])

        # start VCP VMs, we delay the start of vFPC to consume less CPU
        self.start_vcp()

        run_command(["socat", "TCP-LISTEN:22,fork", "TCP:127.0.0.1:2022"], background=True)
        run_command(["socat", "TCP-LISTEN:830,fork", "TCP:127.0.0.1:2830"], background=True)
        while not (self.vcp_started and self.vfpc_started):
            if not self.bootstrap_spin():
                break
        self.bootstrap_end()
        stop_time = datetime.datetime.now()
        self.logger.info("Startup complete in: %s" % (stop_time - start_time))



    def start_vcp(self):
        """ Start the VCP
        """
        self.logger.info("Starting VCP VM")

        # start VCP VM (RE)
        cmd = ["qemu-system-x86_64", "-display", "none", "-m", str(self.ram),
               "-serial", "telnet:0.0.0.0:5000,server,nowait",
               "-drive", "if=ide,file=%s" % self.image,
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

        self.p_vcp = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        try:
            self.p_vcp.communicate('', 1)
        except:
            pass

        run_command(["brctl", "addif", "int_cp", "vcp-int"])
        run_command(["ip", "link", "set", "vcp-int", "up"])

        self.tn_vcp = telnetlib.Telnet("127.0.0.1", 5000)



    def start_vfpc(self):
        """ Start the vFPC
        """
        # start VFP VM
        self.logger.info("Starting vFPC VM")

        cmd = ["kvm", "-display", "none", "-m", "4096",
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

        if self.version_info[0] == 15:
            # dummy interface. not sure why vFPC wants it. version 16 doesn't
            # need it while version 15 does. Not sure about older versions nor
            # do I know if all version 15 or version 16 act the same. I've only
            # tested with vmx-bundle-15.1F6.9.tgz  vmx-bundle-16.1R1.7.tgz to
            # determine this behaviour.
            cmd.extend(["-device", "virtio-net-pci,netdev=dummy,mac=%s" % gen_mac(0)])
            cmd.extend(["-netdev", "tap,ifname=vfpc-dummy,id=dummy,script=no,downscript=no"])

        for i in range(1, self.num_nics):
            cmd.extend(["-device", "virtio-net-pci,netdev=p%(i)02d,mac=%(mac)s"
                       % { 'i': i, 'mac': gen_mac(i) }])
            cmd.extend(["-netdev", "socket,id=p%(i)02d,listen=:100%(i)02d"
                       % { 'i': i }])

        self.p_vfpc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        try:
            self.p_vfpc.communicate('', 1)
        except:
            pass

        run_command(["brctl", "addif", "int_cp", "vfpc-int"])
        run_command(["ip", "link", "set", "vfpc-int", "up"])

        # setup telnet connection
        self.tn_vfpc = telnetlib.Telnet("127.0.0.1", 5001)



    def stop_vcp(self):
        self.p_vcp.terminate()
        try:
            self.p_vcp.communicate(timeout=10)
        except:
            self.p_vcp.kill()
            self.p_vcp.communicate(timeout=10)


    def stop_vfpc(self):
        try:
            self.p_vfpc.terminate()
        except ProcessLookupError:
            return

        try:
            self.p_vfpc.communicate(timeout=10)
        except:
            self.p_vfpc.kill()
            self.p_vfpc.communicate(timeout=10)


    def bootstrap_spin(self):
        """ This function should be called periodically to do work.

            returns False when it has failed and given up, otherwise True
        """

        if self.spins > 300:
            # too many spins with no result -> give up
            self.logger.error("startup took too long - giving up")
            return False

        (ridx, match, res) = self.tn_vcp.expect([b"login:", b"root@(%|:~ #)"], 1)
        if match: # got a match!
            if ridx == 0: # matched login prompt, so should login
                self.logger.info("matched login prompt")
                self.wait_write("root", wait=None)
                self.start_vfpc()
            if ridx == 1:
                # run main config!
                self.bootstrap_config()
                self.vcp_started = True
        else:
            # no match, if we saw some output from the router it's probably
            # booting, so let's give it some more time
            if res != b'':
                self.logger.trace("OUTPUT VCP: %s" % res.decode())
                # reset spins if we saw some output
                self.spins = 0

        self.spins += 1

        if self.vcp_started and not self.vfpc_started:
            self.logger.debug("tickling vFPC")
            self.tn_vfpc.write(b"\r")

        if self.tn_vfpc is not None:
            (ridx, match, res) = self.tn_vfpc.expect([b"localhost login", b"mounting /dev/sda2 on /mnt failed"], 1)
            if match:
                if ridx == 0: # got login - vFPC start succeeded!
                    self.logger.info("vFPC successfully started")
                    self.vfpc_started = True
                if ridx == 1: # vFPC start failed - restart it
                    self.logger.info("vFPC start failed, restarting")
                    self.stop_vfpc()
                    self.start_vfpc()
            if res != b'':
                self.logger.trace("OUTPUT VFPC: %s" % res.decode())

        return True


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
        self.tn_vcp.close()
        self.tn_vfpc.close()


    def wait_write(self, cmd, wait='#', timeout=None):
        """ Wait for something and then send command
        """
        if wait:
            self.logger.trace("Waiting for %s" % wait)
            while True:
                (ridx, match, res) = self.tn_vcp.expect([wait.encode(), b"Retry connection attempts"], timeout=timeout)
                if match:
                    if ridx == 0:
                        break
                    if ridx == 1:
                        self.tn_vcp.write("yes\r".encode())
            self.logger.trace("Read: %s" % res.decode())
        self.logger.debug("writing to serial console: %s" % cmd)
        self.tn_vcp.write("{}\r".format(cmd).encode())



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
