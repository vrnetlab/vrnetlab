#!/usr/bin/env python3

import datetime
import logging
import os
import random
import subprocess
import telnetlib

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


    def __init__(self, username, password):
        self.logger = logging.getLogger()

        # username / password to configure
        self.username = username
        self.password = password

        self.running = False
        self.spins = 0
        self.p = None
        self.tn = None

        #  various settings
        self.ram = 4096
        self.num_nics = 20
        self.disk_image = None



    def start(self):
        self.logger.info("Starting %s" % self.__class__.__name__)
        self.start_time = datetime.datetime.now()

        self.qemu_args = ["qemu-system-x86_64", "-display", "none",
                          "-m", str(self.ram), "-serial",
                          "telnet:0.0.0.0:5000,server,nowait", "-hda",
                          self.disk_image ]

        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            self.qemu_args.insert(1, '-enable-kvm')

        # mgmt interface is special - we use qemu user mode network
        self.qemu_args.append("-device")
        self.qemu_args.append("e1000,netdev=p%(i)02d,mac=%(mac)s"
                              % { 'i': 0, 'mac': gen_mac(0) })
        self.qemu_args.append("-netdev")
        self.qemu_args.append("user,id=p%(i)02d,net=10.0.0.0/24,hostfwd=tcp::2022-10.0.0.15:22,hostfwd=tcp::2830-10.0.0.15:830"
                   % { 'i': 0 })

        for i in range(1, self.num_nics):
            self.qemu_args.append("-device")
            self.qemu_args.append("e1000,netdev=p%(i)02d,mac=%(mac)s"
                       % { 'i': i, 'mac': gen_mac(i) })
            self.qemu_args.append("-netdev")
            self.qemu_args.append("socket,id=p%(i)02d,listen=:100%(i)02d"
                       % { 'i': i })

        self.logger.debug(self.qemu_args)

        self.p = subprocess.Popen(self.qemu_args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True)

        try:
            self.p.communicate(timeout=1)
        except:
            pass

        self.tn = telnetlib.Telnet("127.0.0.1", 5000)


    def stop(self):
        self.running = False


    def wait_write(self, cmd, wait='#'):
        """ Wait for something and then send command
        """
        if wait:
            self.logger.trace("waiting for '%s' on serial console" % wait)
            res = self.tn.read_until(wait.encode())
            self.logger.trace("read from serial console: %s" % res.decode())
        self.logger.debug("writing to serial console: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())


    def work(self):
        self.check_qemu()
        if not self.running:
            self.bootstrap_spin()


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
        self.logger.debug("STDOUT: %s" % outs)
        self.logger.debug("STDERR: %s" % errs)

        if errs != "":
            self.logger.debug("KVM error, restarting")
            self.update_health(2, "KVM error, restarting")
            self.stop()
            self.start()



class VR:
    def __init__(self, username, password):
        self.logger = logging.getLogger()


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
        run_command(["socat", "TCP-LISTEN:830,fork", "TCP:127.0.0.1:2830"], background=True)

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
