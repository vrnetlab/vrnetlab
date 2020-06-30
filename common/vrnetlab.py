#!/usr/bin/env python3

import datetime
import logging
import math
import os
import random
import re
import subprocess
import telnetlib
import time

MAX_RETRIES=60

def gen_mac(last_octet=None):
    """ Generate a random MAC address that is in the qemu OUI space and that
        has the given last octet.
    """
    return "52:54:00:%02x:%02x:%02x" % (
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            last_octet
        )



def run_command(cmd, cwd=None, background=False,shell=False):
    res = None
    try:
        if background:
            p = subprocess.Popen(cmd, cwd=cwd)
        else:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd, shell=shell)
            res = p.communicate()
    except:
        pass
    return res



class VM:
    def __str__(self):
        return self.__class__.__name__


    def __init__(self, username, password, disk_image=None, num=0, ram=4096):
        self.logger = logging.getLogger()

        # username / password to configure
        self.username = username
        self.password = password

        self.num = num
        self.image = disk_image

        self.running = False
        self.spins = 0
        self.p = None
        self.tn = None

        #  various settings
        self.uuid = None
        self.fake_start_date = None
        self.nic_type = "e1000"
        self.num_nics = 0
        self.nics_per_pci_bus = 26 # tested to work with XRv
        self.smbios = []
        self.meshnet = False # Default to not do meshnet
        overlay_disk_image = re.sub(r'(\.[^.]+$)', r'-overlay\1', disk_image)

        if not os.path.exists(overlay_disk_image):
            self.logger.debug("Creating overlay disk image")
            run_command(["qemu-img", "create", "-f", "qcow2", "-b", disk_image, overlay_disk_image])

        self.qemu_args = ["qemu-system-x86_64", "-display", "none", "-machine", "pc" ]
        self.qemu_args.extend(["-monitor", "tcp:0.0.0.0:40%02d,server,nowait" % self.num])
        self.qemu_args.extend(["-m", str(ram),
                               "-serial", "telnet:0.0.0.0:50%02d,server,nowait" % self.num,
                               "-drive", "if=ide,file=%s" % overlay_disk_image])
        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            self.qemu_args.insert(1, '-enable-kvm')



    def start(self):
        self.logger.info("Starting %s" % self.__class__.__name__)
        self.start_time = datetime.datetime.now()

        cmd = list(self.qemu_args)

        # uuid
        if self.uuid:
            cmd.extend(["-uuid", self.uuid])

        # do we have a fake start date?
        if self.fake_start_date:
            cmd.extend(["-rtc", "base=" + self.fake_start_date])

        # smbios
        for e in self.smbios:
            cmd.extend(["-smbios", e])

        # setup PCI buses
        for i in range(1, math.ceil(self.num_nics / self.nics_per_pci_bus) + 1):
            cmd.extend(["-device", "pci-bridge,chassis_nr={},id=pci.{}".format(i, i)])

        # generate mgmt NICs
        cmd.extend(self.gen_mgmt())
        # generate normal NICs
        cmd.extend(self.gen_nics())

        self.logger.debug(cmd)

        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, universal_newlines=True)

        try:
            outs, errs = self.p.communicate(timeout=2)
            self.logger.info("STDOUT: %s" % outs)
            self.logger.info("STDERR: %s" % errs)
        except:
            pass

        for i in range(1, MAX_RETRIES+1):
            try:
                self.qm = telnetlib.Telnet("127.0.0.1", 4000 + self.num)
                break
            except:
                self.logger.info("Unable to connect to qemu monitor (port {}), retrying in a second (attempt {})".format(4000 + self.num, i))
                time.sleep(1)
            if i == MAX_RETRIES:
                raise QemuBroken("Unable to connect to qemu monitor on port {}".format(4000 + self.num))

        for i in range(1, MAX_RETRIES+1):
            try:
                self.tn = telnetlib.Telnet("127.0.0.1", 5000 + self.num)
                break
            except:
                self.logger.info("Unable to connect to qemu monitor (port {}), retrying in a second (attempt {})".format(5000 + self.num, i))
                time.sleep(1)
            if i == MAX_RETRIES:
                raise QemuBroken("Unable to connect to qemu monitor on port {}".format(5000 + self.num))
        try:
            outs, errs = self.p.communicate(timeout=2)
            self.logger.info("STDOUT: %s" % outs)
            self.logger.info("STDERR: %s" % errs)
        except:
            pass


    def create_bridges(self):
        """ Create a linux bridge for every attached eth interface
            Returns list of bridge names 
        """
        run_command(["mkdir", "-p", "/etc/qemu"]) # This is to whitlist all bridges
        run_command(["echo 'allow all' > /etc/qemu/bridge.conf"], shell=True)

        bridges = list()
        intfs = [x for x in os.listdir('/sys/class/net/') if 'eth' in x if x != 'eth0']
        intfs.sort()

        self.logger.info("Creating bridges for interfaces: %s" % intfs)

        for idx, intf in enumerate(intfs):
            run_command(["ip", "link", "add", "name", "br-%s" % idx, "type", "bridge"], background=True)
            run_command(["ip", "link", "set", "br-%s" % idx, "up"], background=True)
            run_command(["ip", "link", "set", intf,  "master", "br-%s" % idx], background=True)
            run_command(["echo 16384 > /sys/class/net/br-%s/bridge/group_fwd_mask" % idx], shell=True)
            bridges.append("br-%s" % idx)
        return bridges

    def gen_mgmt(self):
        """ Generate qemu args for the mgmt interface(s)
        """
        res = []
        # mgmt interface is special - we use qemu user mode network
        res.append("-device")
        # vEOS-lab requires its Ma1 interface to be the first in the bus, so let's hardcode it
        if 'vEOS-lab' in self.image:
            res.append(self.nic_type + ",netdev=p%(i)02d,mac=%(mac)s,bus=pci.1,addr=0x2"
                       % { 'i': 0, 'mac': gen_mac(0) })
        else:
            res.append(self.nic_type + ",netdev=p%(i)02d,mac=%(mac)s"
                       % { 'i': 0, 'mac': gen_mac(0) })
        res.append("-netdev")
        res.append("user,id=p%(i)02d,net=10.0.0.0/24,tftp=/tftpboot,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=udp::2161-10.0.0.15:161,hostfwd=tcp::2830-10.0.0.15:830,hostfwd=tcp::2080-10.0.0.15:80,hostfwd=tcp::2443-10.0.0.15:443" % { 'i': 0 })

        return res


    def gen_nics(self):
        """ Generate qemu args for the normal traffic carrying interface(s)
        """
        res = []
        if self.num_nics > 0:
            bridges = self.create_bridges()
        # vEOS-lab requires its Ma1 interface to be the first in the bus, so start normal nics at 2
        if 'vEOS-lab' in self.image:
            range_start = 2
        else:
            range_start = 1
        for i in range(range_start, self.num_nics+1):
            # calc which PCI bus we are on and the local add on that PCI bus
            pci_bus = math.floor(i/self.nics_per_pci_bus) + 1
            addr = (i % self.nics_per_pci_bus) + 1

            res.append("-device")
            res.append("%(nic_type)s,netdev=p%(i)02d,mac=%(mac)s,bus=pci.%(pci_bus)s,addr=0x%(addr)x" % {
                       'nic_type': self.nic_type,
                       'i': i,
                       'pci_bus': pci_bus,
                       'addr': addr,
                       'mac': gen_mac(i)
                    })
            if self.meshnet: # Meshnet logic
                if i <= len(bridges):
                    bridge = bridges[i-1] # We're starting from 0
                    res.append("-netdev")
                    res.append("bridge,id=p%(i)02d,br=%(bridge)s"
                                % { 'i': i, 'bridge': bridge })
                else: # We don't create more interfaces than we have bridges
                    del res[-2:] # Removing recently added interface
            else:      
                res.append("-netdev")
                res.append("socket,id=p%(i)02d,listen=:100%(i)02d"
                           % { 'i': i })
        return res



    def stop(self):
        """ Stop this VM
        """
        self.running = False

        try:
            self.p.terminate()
        except ProcessLookupError:
            return

        try:
            self.p.communicate(timeout=10)
        except:
            try:
                # this construct is included as an example at
                # https://docs.python.org/3.6/library/subprocess.html but has
                # failed on me so wrapping in another try block. It was this
                # communicate() that failed with:
                # ValueError: Invalid file object: <_io.TextIOWrapper name=3 encoding='ANSI_X3.4-1968'>
                self.p.kill()
                self.p.communicate(timeout=10)
            except:
                # just assume it's dead or will die?
                self.p.wait(timeout=10)



    def restart(self):
        """ Restart this VM
        """
        self.stop()
        self.start()



    def wait_write(self, cmd, wait='#', con=None):
        """ Wait for something on the serial port and then send command

            Defaults to using self.tn as connection but this can be overridden
            by passing a telnetlib.Telnet object in the con argument.
        """
        con_name = 'custom con'
        if con is None:
            con = self.tn

        if con == self.tn:
            con_name = 'serial console'
        if con == self.qm:
            con_name = 'qemu monitor'

        if wait:
            self.logger.trace("waiting for '%s' on %s" % (wait, con_name))
            res = con.read_until(wait.encode())
            self.logger.trace("read from %s: %s" % (con_name, res.decode()))
        self.logger.debug("writing to %s: %s" % (con_name, cmd))
        con.write("{}\r".format(cmd).encode())


    def work(self):
        self.check_qemu()
        if not self.running:
            try:
                self.bootstrap_spin()
            except EOFError:
                self.logger.error("Telnet session was disconncted, restarting")
                self.restart()



    def check_qemu(self):
        """ Check health of qemu. This is mostly just seeing if there's error
            output on STDOUT from qemu which means we restart it.
        """
        if self.p is None:
            self.logger.debug("VM not started; starting!")
            self.start()

        # check for output
        try:
            outs, errs = self.p.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            return
        self.logger.info("STDOUT: %s" % outs)
        self.logger.info("STDERR: %s" % errs)

        if errs != "":
            self.logger.debug("KVM error, restarting")
            self.stop()
            self.start()



class VR:
    def __init__(self, username, password):
        self.logger = logging.getLogger()

        try:
            os.mkdir("/tftpboot")
        except:
            pass


    def update_health(self, exit_status, message):
        health_file = open("/health", "w")
        health_file.write("%d %s" % (exit_status, message))
        health_file.close()



    def start(self):
        """ Start the virtual router
        """
        self.logger.debug("Starting vrnetlab %s" % self.__class__.__name__)
        self.logger.debug("VMs: %s" % self.vms)
        run_command(["socat", "TCP-LISTEN:22,fork", "TCP:127.0.0.1:2022"], background=True)
        run_command(["socat", "UDP-LISTEN:161,fork", "UDP:127.0.0.1:2161"], background=True)
        run_command(["socat", "TCP-LISTEN:830,fork", "TCP:127.0.0.1:2830"], background=True)
        run_command(["socat", "TCP-LISTEN:80,fork", "TCP:127.0.0.1:2080"], background=True)
        run_command(["socat", "TCP-LISTEN:443,fork", "TCP:127.0.0.1:2443"], background=True)

        started = False
        while True:
            all_running = True
            for vm in self.vms:
                vm.work()
                if vm.running != True:
                    all_running = False

            if all_running:
                self.update_health(0, "running")
                started = True
            else:
                if started:
                    self.update_health(1, "VM failed - restarting")
                else:
                    self.update_health(1, "starting")


class QemuBroken(Exception):
    """ Our Qemu instance is somehow broken
    """
