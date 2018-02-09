#!/usr/bin/env python3

import datetime
import logging
import os
import random
import re
import signal
import subprocess
import sys
import socket
import telnetlib
import time
import math
import IPy
import pexpect
import os
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

class simulator_VM(vrnetlab.VM):
    def __init__(self, username, password):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e
        
        self.ram = 16384
        self.vcpu = 6
        self.disk_size = '40G'
        super(simulator_VM, self).__init__(username, password, disk_image=disk_image, num=0, ram=self.ram)
        self.logger = logging.getLogger()

        self.num_nics = 14
        self.wait_time = 20
        self.nic_type = 'virtio-net-pci'
        vrnetlab.run_command(["qemu-img","create","-f","qcow2","DataDisk.qcow2",self.disk_size])
        self.qemu_args.extend(["-drive","if=virtio,format=qcow2,file=DataDisk.qcow2"])
        self.qemu_args.extend(["-smp", str(self.vcpu),
                               "-cpu", "host"])
        self.qemu_args.extend(["-D", "/var/log/qemu.log"])                       

    def start(self):
        self.logger.info("Starting %s" % self.__class__.__name__)
        self.start_time = datetime.datetime.now()

        cmd = list(self.qemu_args)

        for i in range(1, math.ceil(self.num_nics / self.nics_per_pci_bus) + 1):
            cmd.extend(["-device", "pci-bridge,chassis_nr={},id=pci.{}".format(i, i)])

        cmd.extend(self.gen_mgmt())
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
        
    def wait_write(self, cmd, wait):
        
        idx = self.ssh.expect([pexpect.TIMEOUT, wait])
        if idx == 1:
            self.ssh.sendline(cmd)
            self.logger.debug(wait + " " + cmd)
        else:
            raise
    
    def user_config(self, user, old_passwd, new_passwd):

        try:
            self.wait_write('yes', "Are you sure you want to continue connecting")
            self.wait_write(old_passwd, "%s@%s's password: " % (user, '127.0.0.1'))
            self.wait_write('y', "The password needs to be changed. Change now?")
            self.wait_write(old_passwd, "Please enter old password:")
            self.wait_write(new_passwd, "Please enter new password:")
            self.wait_write(new_passwd, "Please confirm new password:")
        except:
            raise
            return

    def kill_ssh_process(self):
        """
           depend on ssh.pid, kill it, if exception, pass
        """
        try:
            os.kill(self.ssh.pid, signal.SIGKILL)
        except:
            pass

    def bootstrap_spin(self):
        """

        """
        hosts = "/root/.ssh/known_hosts"
        if os.path.isfile(hosts):
            os.remove(hosts)

        self.ssh = pexpect.spawn('ssh -l %s %s ' % ('omuser', '127.0.0.1'))
        try:
            self.user_config('omuser', 'User_hw123', 'Changeme_123')
            time.sleep(1)

        except:
            self.logger.trace("SSH Connect TimeOut, Simulator Device is Booting")
            # kill child subprocess 
            self.kill_ssh_process()
            time.sleep(self.wait_time)
            return

        self.bootstrap_config()
        self.running = True
        self.kill_ssh_process()
        # calc startup time
        startup_time = datetime.datetime.now() - self.start_time
        self.logger.info("Startup complete in: %s" % startup_time)

    def bootstrap_config(self):
        """
        
        """
        self.wait_write('system-view', "<HUAWEI>")
        self.wait_write('aaa', "[~HUAWEI]")
        self.wait_write('local-user %s password' % self.username, "[~HUAWEI-aaa]")
        self.wait_write('Changeme_123', "Enter Password:")
        self.wait_write('Changeme_123', "Confirm Password:")
        self.wait_write('local-user %s service-type ssh' % self.username, "[*HUAWEI-aaa]")
        self.wait_write('local-user %s user-group manage-ug' % self.username, "[*HUAWEI-aaa]")
        self.wait_write('commit', "[*HUAWEI-aaa]")
        self.wait_write('quit', "[~HUAWEI-aaa]")
        self.wait_write('quit', "[~HUAWEI]")
        self.wait_write('quit', "<HUAWEI>")

        hosts = "/root/.ssh/known_hosts"
        if os.path.isfile(hosts):
            os.remove(hosts)

        self.ssh = pexpect.spawn('ssh -l %s %s ' % (self.username, '127.0.0.1'))
        self.user_config(self.username, 'Changeme_123', self.password)


class simulator(vrnetlab.VR):

    def __init__(self, username, password):
         super(simulator, self).__init__(username, password)
         self.vms = [ simulator_VM(username, password)]


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

    vr = simulator(args.username, args.password)
    vr.start()
