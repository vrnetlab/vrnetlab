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

# Global list of ports that we want to set up forwarding from container IP ->
# mgmt IP of router (usually 10.0.0.15). Each entry consists of the protocol,
# the source port (on the outside of the container) and the destination port
# (on the virtual router).
HOST_FWDS = [
    ('tcp', 22, 22),      # SSH
    ('udp', 161, 161),    # SNMP
    ('tcp', 830, 830),    # NETCONF
    ('tcp', 80, 80),      # HTTP
    ('tcp', 443, 443),    # HTTPS
]

def gen_mac(last_octet=None):
    """ Generate a random MAC address that is in the qemu OUI space and that
        has the given last octet.
    """
    return "52:54:00:%02x:%02x:%02x" % (
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            last_octet
        )



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



class VM:
    def __str__(self):
        return self.__class__.__name__


    def __init__(self, username, password, disk_image=None, num=0, ram=4096):
        self.logger = logging.getLogger()
        self.start_time = datetime.datetime.now()

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

        self.qemu_args = ["qemu-system-x86_64", "-display", "none", "-machine", "pc" ]
        self.qemu_args.extend(["-monitor", "tcp:0.0.0.0:40%02d,server,nowait" % self.num])
        self.qemu_args.extend(["-m", str(ram),
                               "-serial", "telnet:0.0.0.0:50%02d,server,nowait" % self.num])
        self.qemu_args.extend(self.create_overlay_image())
        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            self.qemu_args.insert(1, '-enable-kvm')



    def start(self):
        self.logger.info("Starting %s" % self.__class__.__name__)

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

    def gen_host_forwards(self, mgmt_ip='10.0.0.15', offset=2000):
        """Generate the host forward argument for qemu
        HOST_FWDS contain the ports we want to forward and allows mapping a
        container (source) port to a different destination port on the VR/VM.
        We do a straight mapping here and let socat do the port mapping. Since
        multiple source ports can be mapped to the same destination port, we
        first unique the set of ports.
        """
        fwd_ports = {(proto, dst_port) for proto, src_port, dst_port in HOST_FWDS}
        # hostfwd=tcp::2022-10.0.0.15:22,...
        return ",".join("hostfwd=%s::%d-%s:%d" % (proto, port + offset, mgmt_ip, port) for proto, port in fwd_ports)


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
        res.append("user,id=p%(i)02d,net=10.0.0.0/24,tftp=/tftpboot,%(hostfwd)s" % { 'i': 0, 'hostfwd': self.gen_host_forwards() })

        return res


    def gen_nics(self):
        """ Generate qemu args for the normal traffic carrying interface(s)
        """
        res = []
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
            res.append("-netdev")
            res.append("socket,id=p%(i)02d,listen=:%(j)02d"
                       % { 'i': i, 'j': i + 10000 })
        return res


    def create_overlay_image(self):
        """Creates an overlay image if one does not exist and return
           an array of parameters to extend qemu_args,
           A subclass may want to override this for using specific drive id.
        """
        overlay_disk_image = re.sub(r'(\.[^.]+$)', r'-overlay\1', self.image)

        if not os.path.exists(overlay_disk_image):
            self.logger.debug("Creating overlay disk image")
            run_command(["qemu-img", "create", "-f", "qcow2", "-b", self.image, overlay_disk_image])
        return ["-drive", "if=ide,file=%s" % overlay_disk_image]


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
                self.logger.error("Telnet session was disconnected, restarting")
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

    def start_socat(self, src_offset=0, dst_offset=2000):
        for proto, src_port, dst_port in HOST_FWDS:
            run_command(["socat", "%s-LISTEN:%d,fork" % (proto.upper(), src_port + src_offset),
                         "%s:127.0.0.1:%d" % (proto.upper(), dst_port + dst_offset)],
                         background=True)

    def start(self):
        """ Start the virtual router
        """
        self.logger.debug("Starting vrnetlab %s", self.__class__.__name__)
        self.logger.debug("VMs: %s", self.vms)
        self.start_socat()

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
