#!/usr/bin/env python3

import datetime
import logging
import os
import re
import select
import signal
import subprocess
import sys
import time

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



class VMX_vcp(vrnetlab.VM):
    def __init__(self, username, password, image, version, dual_re=False, re_instance=0, install_mode=False):
        self.dual_re = dual_re
        self.num = re_instance
        self.install_mode = install_mode
        super(VMX_vcp, self).__init__(username, password, disk_image=self._get_file_in_vcp_folder(image), ram=2048, num=re_instance)

        self.num_nics = 0
        self.qemu_args.extend(["-drive", "if=ide,file=" + self._get_file_in_vcp_folder("vmxhdd.img")])
        if dual_re:
            product = "VM-vcp_vmx2-161-dualre-{}".format(re_instance)
        else:
            product = "VM-vcp_vmx2-161-re-0"
        self.smbios = ["type=0,vendor=Juniper",
                       "type=1,manufacturer=Juniper,product=%s,version=0.1.0" % product]
        # insert bootstrap config file into metadata image
        if self.install_mode:
            self.insert_bootstrap_config()
        else:
            self.insert_extra_config()
        # add metadata image if it exists
        if os.path.exists(self._metadata_usb):
            self.qemu_args.extend(
                 ["-usb", "-drive", "id=my_usb_disk,media=disk,format=raw,file={},if=none".format(self._metadata_usb),
                 "-device", "usb-storage,drive=my_usb_disk"])

    def _get_file_in_vcp_folder(self, file):
        return "/vmx/re{}/{}".format(self.num if self.dual_re else '', file)

    @property
    def _metadata_usb(self):
        return self._get_file_in_vcp_folder("metadata-usb-re{}.img".format(self.num if self.dual_re else ''))

    @property
    def _vcp_int(self):
        return "vcp-int{}".format(self.num if self.dual_re else '')

    def start(self):
        # use parent class start() function
        super(VMX_vcp, self).start()
        # add interface to internal control plane bridge
        if not self.install_mode:
            vrnetlab.run_command(["brctl", "addif", "int_cp", self._vcp_int])
            vrnetlab.run_command(["ip", "link", "set", self._vcp_int, "up"])


    def gen_mgmt(self):
        """ Generate mgmt interface(s)

            We override the default function since we want a virtio NIC to the
            vFPC
        """
        # call parent function to generate first mgmt interface (e1000)
        res = super(VMX_vcp, self).gen_mgmt()
        # install mode doesn't need host port forwarding rules. if running in
        # dual-re mode, replace host port forwarding rules for the backup
        # routing engine
        if self.install_mode:
            res[-1] = re.sub(r',hostfwd.*', '', res[-1])
        elif self.dual_re and self.num == 1:
            res[-1] = re.sub(r',hostfwd.*', self.gen_host_forwards(mgmt_ip='10.0.0.16', offset=3000), res[-1])

        if not self.install_mode:
            # add virtio NIC for internal control plane interface to vFPC
            res.append("-device")
            res.append("virtio-net-pci,netdev=%s,mac=%s" % (self._vcp_int, vrnetlab.gen_mac(1)))
            res.append("-netdev")
            res.append("tap,ifname=%(_vcp_int)s,id=%(_vcp_int)s,script=no,downscript=no" % { '_vcp_int': self._vcp_int })
        return res


    def bootstrap_spin(self):
        """ This function should be called periodically to do work.

            returns False when it has failed and given up, otherwise True
        """

        if self.spins > 300:
            # too many spins with no result -> restart
            self.logger.warning("no output from serial console, restarting VCP")
            self.stop()
            self.start()
            self.spins = 0
            return

        (ridx, match, res) = self.tn.expect([b"(?<!Last )login:", b"root@(%|[^:]*:~ #)"], 1)
        if match: # got a match!
            if ridx == 0: # matched login prompt, so should login
                self.logger.info("matched login prompt")
                self.wait_write("root", wait=None)
                self.wait_write("VR-netlab9", "Password:")
            if ridx == 1:
                if self.install_mode:
                    self.logger.info("requesting power-off")
                    self.wait_write("cli", None)
                    self.wait_write("request system power-off", '>')
                    self.wait_write("yes", 'Power Off the system')
                    self.running = True
                    return
                # run extra config!
                self.do_extra_config()
                self.running = True
                self.tn.close()
                # calc startup time
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s" % startup_time)
                return

        else:
            # no match, if we saw some output from the router it's probably
            # booting, so let's give it some more time
            if res != b'':
                self.logger.trace("OUTPUT VCP[%d]: %s" % (self.num, res.decode()))
                # reset spins if we saw some output
                self.spins = 0

        self.spins += 1



    def do_extra_config(self):
        """ Do the actual bootstrap config
        """
        self.wait_write("mount_msdosfs /dev/da0 /mnt", None)
        self.wait_write("cli", None)
        self.wait_write("configure", '>', 10)
        self.wait_write("load merge /mnt/extra-config.conf")
        self.wait_write("commit")
        self.wait_write("exit")


    def wait_write(self, cmd, wait='#', timeout=None):
        """ Wait for something and then send command
        """
        if wait:
            self.logger.trace("Waiting for %s" % wait)
            while True:
                (ridx, match, res) = self.tn.expect([wait.encode(), b"Retry connection attempts"], timeout=timeout)
                if match:
                    if ridx == 0:
                        break
                    if ridx == 1:
                        self.tn.write("yes\r".encode())
            self.logger.trace("Read: %s" % res.decode())
        self.logger.debug("writing to serial console: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())

    def insert_bootstrap_config(self):
        vrnetlab.run_command(["mount", "-o", "loop", self._metadata_usb, "/mnt"])
        vrnetlab.run_command(["mkdir", "/tmp/vmm-config"])
        vrnetlab.run_command(["tar", "-xzvf", "/mnt/vmm-config.tgz", "-C", "/tmp/vmm-config"])
        vrnetlab.run_command(["mkdir", "/tmp/vmm-config/config"])
        vrnetlab.run_command(["cp", "/juniper.conf", "/tmp/vmm-config/config/"])
        vrnetlab.run_command(["tar", "zcf", "vmm-config.tgz", "-C", "/tmp/vmm-config", "."])
        vrnetlab.run_command(["cp", "vmm-config.tgz", "/mnt/vmm-config.tgz"])
        vrnetlab.run_command(["umount", "/mnt"])

    def insert_extra_config(self):
        extra_config = os.getenv('EXTRA_CONFIG')
        if extra_config:
            self.logger.debug('extra_config = ' + extra_config)
            vrnetlab.run_command(["mount", "-o", "loop", self._metadata_usb, "/mnt"])
            with open('/mnt/extra-config.conf', 'w') as f:
                f.write(extra_config)
            vrnetlab.run_command(["umount", "/mnt"])


class VMX_vfpc(vrnetlab.VM):
    def __init__(self, version):
        # "Hardcode" the num to 3 for this VM. This gives us a static mapping
        # for the console port (5002) independent of how man VCPs are running
        super(VMX_vfpc, self).__init__(None, None, disk_image = "/vmx/vfpc.img", num=3)
        self.version = version
        self.num_nics = 96

        self.nic_type = "virtio-net-pci"
        self.qemu_args.extend(["-cpu", "SandyBridge", "-M", "pc", "-smp", "3"])
        # add metadata image if it exists
        if os.path.exists("/vmx/metadata-usb-fpc0.img"):
            self.qemu_args.extend(
                ["-usb", "-drive", "id=fpc_usb_disk,media=disk,format=raw,file=/vmx/metadata-usb-fpc0.img,if=none",
                 "-device", "usb-storage,drive=fpc_usb_disk"])



    def gen_mgmt(self):
        res = []
        # mgmt interface
        res.extend(["-device", "virtio-net-pci,netdev=mgmt,mac=%s" % vrnetlab.gen_mac(0)])
        res.extend(["-netdev", "user,id=mgmt,net=10.0.0.0/24"])
        # internal control plane interface to vFPC
        res.extend(["-device", "virtio-net-pci,netdev=vfpc-int,mac=%s" %
                    vrnetlab.gen_mac(0)])
        res.extend(["-netdev",
                    "tap,ifname=vfpc-int,id=vfpc-int,script=no,downscript=no"])

        if self.version in ('15.1F6.9', '16.1R2.11', '17.1R1.8', '17.2R1.13', '18.2R2.6', '18.4R1.8', '18.4R3.3'):
            # dummy interface for some vMX versions - not sure why vFPC wants
            # it but without it we get a misalignment
            res.extend(["-device", "virtio-net-pci,netdev=dummy,mac=%s" % vrnetlab.gen_mac(0)])
            res.extend(["-netdev", "tap,ifname=vfpc-dummy,id=dummy,script=no,downscript=no"])

        return res



    def start(self):
        # use parent class start() function
        super(VMX_vfpc, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(["brctl", "addif", "int_cp", "vfpc-int"])
        vrnetlab.run_command(["ip", "link", "set", "vfpc-int", "up"])



    def bootstrap_spin(self):
        (ridx, match, res) = self.tn.expect([b"localhost login", b"qemux86-64 login", b"mounting /dev/sda2 on /mnt failed"], 1)
        if match:
            if ridx in (0, 1): # got login - vFPC start succeeded!
                self.logger.info("vFPC successfully started")
                self.running = True
                self.tn.close()
            if ridx == 2: # vFPC start failed - restart it
                self.logger.info("vFPC start failed, restarting")
                self.stop()
                self.start()
        if res != b'':
            pass
            #self.logger.trace("OUTPUT VFPC: %s" % res.decode())

        return



class VMX(vrnetlab.VR):
    """ Juniper vMX router
    """

    def __init__(self, username, password, dual_re=False):
        self.version = None
        self.version_info = []
        self.read_version()
        self.dual_re = dual_re

        super(VMX, self).__init__(username, password)

        if not dual_re:
            self.vms = [ VMX_vcp(username, password, self.vcp_image, self.version), VMX_vfpc(self.version) ]
        else:
            self.vms = [ VMX_vcp(username, password, self.vcp_image, self.version, dual_re=True, re_instance=0),
                         VMX_vcp(username, password, self.vcp_image, self.version, dual_re=True, re_instance=1),
                         VMX_vfpc(self.version) ]


        # set up bridge for connecting VCP with vFPC
        vrnetlab.run_command(["brctl", "addbr", "int_cp"])
        vrnetlab.run_command(["ip", "link", "set", "int_cp", "up"])


    def read_version(self):
        for e in os.listdir("/vmx/re"):
            m = re.search(r"-(([0-9][0-9])\.([0-9])([A-Z])([0-9]+)(\-[SD][0-9]*)?\.([0-9]+))", e)
            if m:
                self.vcp_image = e
                self.version = m.group(1)
                self.version_info = [int(m.group(2)), int(m.group(3)), m.group(4), int(m.group(5)), int(m.group(7))]

    def start(self):
        # Set up socats for re1, with a different offset: $CONTAINER_IP:1022 -> 10.0.0.16:3022
        if self.dual_re:
            self.start_socat(src_offset=1000, dst_offset=3000)

        super(VMX, self).start()


class VMX_installer(VMX):
    """ VMX installer

        Will start the VMX VCP and then shut it down. Booting the VCP for the
        first time requires the VCP itself to load some config and then it will
        restart. Subsequent boots will not require this restart. By running
        this "install" when building the docker image we can decrease the
        normal startup time of the vMX.
    """
    def __init__(self, username, password, dual_re=False):
        self.version = None
        self.version_info = []
        self.read_version()

        super().__init__(username, password, dual_re)

        if not dual_re:
            self.vms = [ VMX_vcp(username, password, self.vcp_image, self.version, install_mode=True) ]
        else:
            # When installing in dual-RE mode, boot a standalone RE and also 2x
            # dualre. The final image will end up with 3 VMs, but we choose
            # which are started with the `--dual-re` option.
            self.vms = [ VMX_vcp(username, password, self.vcp_image, self.version, dual_re=True, re_instance=0, install_mode=True),
                         VMX_vcp(username, password, self.vcp_image, self.version, dual_re=True, re_instance=1, install_mode=True),
                         VMX_vcp(username, password, self.vcp_image, self.version, dual_re=False, re_instance=2, install_mode=True)]

    def install(self):
        self.logger.info("Installing VMX (%d VCP)" % len(self.vms))
        while not all(vcp.running for vcp in self.vms):
            for idx, vcp in enumerate(self.vms):
                if not vcp.running:
                    self.logger.trace("RE[%d]: working" % idx)
                    vcp.work()
        self.logger.debug("All %d VCPs running" % len(self.vms))

        def waitable_pipes():
            return [vcp.p.stdout for vcp in self.vms if vcp.running] + [vcp.p.stderr for vcp in self.vms if vcp.running]
        # wait for system to shut down cleanly
        while waitable_pipes():
            read_pipes, _, _ = select.select(waitable_pipes(), [],  [])
            for read_pipe in read_pipes:
                for idx, vcp in enumerate(self.vms):
                    if read_pipe in (vcp.p.stdout, vcp.p.stderr):
                        break

                try:
                    vcp.p.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
                except Exception as exc:
                    # assume it's dead
                    self.logger.info("RE[%d]: Can't communicate with qemu process, assuming VM has shut down properly.\n%s" % (idx, str(exc)))
                    vcp.stop()

                try:
                    (ridx, match, res) = vcp.tn.expect([b"Powering system off"], 1)
                    if res != b'':
                        self.logger.trace("RE[%d]: OUTPUT VCP: %s" % (idx, res.decode()))
                except Exception as exc:
                    # assume it's dead
                    self.logger.info("RE[%d]: Can't communicate with qemu process, assuming VM has shut down properly.\n%s" % (idx, str(exc)))
                    vcp.stop()

        self.logger.info("Installation complete")



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--username', default='vrnetlab', help='Username')
    parser.add_argument('--password', default='VR-netlab9', help='Password')
    parser.add_argument('--install', action='store_true', help='Install vMX')
    parser.add_argument('--dual-re', action='store_true', help='Boot dual Routing Engines')
    parser.add_argument('--num-nics', type=int, default=96, help='Number of NICs, this parameter is IGNORED, only added to be compatible with other platforms')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    if args.install:
        vr = VMX_installer(args.username, args.password, args.dual_re)
        vr.install()
    else:
        vr = VMX(args.username, args.password, args.dual_re)
        vr.start()
