#!/usr/bin/env python3

import datetime
import logging
import os
import re
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


class FTDV_vm(vrnetlab.VM):
    
    # FIPS check fails without exposing cpu (ERROR: FIPS Self-Test failure,  fipsPostGFSboxKat)
    def __init__(
        self, hostname, username, password, nics, conn_mode, install_mode=False,
    ):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e

        self.license = False

        super(FTDV_vm, self).__init__(
            username, password, disk_image=disk_image, ram=8192, smp="4,sockets=1,cores=4,threads=1"
        )
        
        self.login_ready = False
        

        self.install_mode = install_mode
        self.num_nics = nics
        self.hostname = hostname
        self.conn_mode = conn_mode
        self.nic_type = "virtio-net-pci"
        overlay_disk_image = re.sub(r"(\.[^.]+$)", r"-overlay\1", disk_image)
        # boot harddrive first
        self.qemu_args.extend(["-boot", "order=c"])
        replace_index = self.qemu_args.index(f"if=ide,file={overlay_disk_image}")
        self.qemu_args[
            replace_index
        ] = f"file={overlay_disk_image},if=none,id=drive-sata-disk0,format=qcow2"
        self.qemu_args.extend(["-device", "ahci,id=ahci0,bus=pci.0"])
        self.qemu_args.extend(
            [
                "-device",
                "ide-hd,drive=drive-sata-disk0,bus=ahci0.0,id=drive-sata-disk0,bootindex=1",
            ]
        )
        if self.install_mode:
            logger.trace("install mode")
            self.image_name = "day0.iso"
            self.create_boot_image()
            # mount config disk with day0-config base config
            self.qemu_args.extend(
                [
                    "-drive",
                    f"if=none,id=day0_disk,file=/{self.image_name},format=raw",
                    "-device",
                    "ide-cd,bus=ide.0,unit=0,drive=day0_disk",
                ]
            )

    def create_boot_image(self):
        """Creates a iso image with a bootstrap configuration"""

        with open("/day0-config", "w") as cfg_file:
            cfg_file.write("#Firepower Threat Defense\n")
            cfg_file.write("{\n")
            cfg_file.write('    "EULA": "accept",\n')
            cfg_file.write(f'    "Hostname": "{self.hostname}",\n')
            cfg_file.write(f'    "AdminPassword": "{self.password}",\n')
            cfg_file.write('    "FirewallMode": "routed",\n')
            cfg_file.write('    "DNS1": "10.0.0.3",\n')
            cfg_file.write('    "DNS2": "",\n')
            cfg_file.write('    "DNS3": "",\n')
            cfg_file.write('    "IPv4Mode": "manual",\n')
            cfg_file.write('    "IPv4Addr": "10.0.0.15",\n')
            cfg_file.write('    "IPv4Mask": "255.255.255.0",\n')
            cfg_file.write('    "IPv4Gw": "10.0.0.2",\n')
            cfg_file.write('    "IPv6Mode": "disabled",\n')
            cfg_file.write('    "IPv6Addr": "",\n')
            cfg_file.write('    "IPv6Mask": "",\n')
            cfg_file.write('    "IPv6Gw": "", \n')
            cfg_file.write('    "FmcIp": "",\n')
            cfg_file.write('    "FmcRegKey": "",\n')
            cfg_file.write('    "FmcNatId": "",\n')
            cfg_file.write('    "ManageLocally":"Yes"\n')
            cfg_file.write("}\n")

        genisoimage_args = [
            "genisoimage",
            "-l",
            "-relaxed-filenames",  # prevents replacing '-' with '_'
            "-o",
            "/" + self.image_name,
            "/day0-config",
        ]

        subprocess.Popen(genisoimage_args)

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 600:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return
        
        (_, l_match, l_res) = self.tn.expect([b"INFO: Power-On Self-Test"], 1)
        if l_match:
            self.logger.debug("LOGIN READY")
            self.login_ready = True
        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        elif l_res != b"":
            self.logger.trace("OUTPUT: %s" % l_res.decode())
            # reset spins if we saw some output
            self.spins = 0
        
        if self.login_ready or not self.install_mode:
            (ridx, match, res) = self.tn.expect([b"login:"], 1)
            if match:  # got a match!
                if ridx == 0:  # login
                    if self.install_mode:
                        # we need to login to trigger the firstboot initial configuration
                        self.wait_write("", None)
                        self.wait_write(self.username, "login:")
                        time.sleep(1)
                        self.wait_write(self.password, None)
                        time.sleep(1)
                        self.wait_write("", None)

                        # shutdown gracefully
                        self.wait_write("shutdown", ">")
                        self.wait_write("YES", "Please enter 'YES' or 'NO':")
                        self.wait_write("", "Unmounting local filesystems...")
                        # wait for filesystems to unmount
                        time.sleep(20)
                        self.running = True
                        return

                    self.logger.debug("matched, login:")
                    self.wait_write("", wait=None)

                    self.bootstrap_config()
                    self.running = True
                    # close telnet connection
                    self.tn.close()
                    # startup time?
                    startup_time = datetime.datetime.now() - self.start_time
                    self.logger.info(f"Startup complete in: {startup_time}")
                    return

        self.spins += 1

        return

    def gen_nics(self):
        """
        Override the default function,
        to get the required number of NICs during install.

        This adds 2 NICs to other 2 created by gen_mgmt() to get the required 4.
        """

        # call parent function
        res = super(FTDV_vm, self).gen_nics()

        if self.install_mode:
            for i in range(1, 3):
                res.append("-device")
                res.append(f"virtio-net-pci,netdev=p{i:02d},mac={vrnetlab.gen_mac(i)}")
                res.append("-netdev")
                res.append(f"tap,ifname=p{i:02d},id=p{i:02d},script=no,downscript=no")
        return res

    def gen_mgmt(self):
        """Generate mgmt interface(s)

        Override the default function since FTDv requires a minimum
        of 4 NICs.
        """
        # call parent function to generate first mgmt interface
        res = super(FTDV_vm, self).gen_mgmt()

        # append FMC management port forwarding
        res[-1] = res[-1] + ",hostfwd=tcp::28305-10.0.0.15:8305"
        vrnetlab.run_command(
            ["socat", "TCP-LISTEN:8305,fork", "TCP:127.0.0.1:28305"],
            background=True,
        )

        # add Diagnostic0/0 interface
        res.append("-device")
        res.append(f"virtio-net-pci,netdev=Diagnostic0-0,mac={vrnetlab.gen_mac(0)}")
        res.append("-netdev")
        res.append("tap,ifname=Diagnostic0-0,id=Diagnostic0-0,script=no,downscript=no")

        return res

    def bootstrap_config(self):
        """Do the actual bootstrap config"""

        # Hostname defaults to 'ftdv' and the day0 config is ignored next boot after install.
        # Although, the management interface config remains intact.
        self.logger.info("applying bootstrap configuration")
        self.wait_write("", None)
        self.wait_write(self.username, "login:")
        self.wait_write(self.password, "Password:")
        # self.wait_write("\r", "Failed logins since the last login:")
        self.wait_write(f"configure network hostname {self.hostname}", ">")
        self.wait_write("exit", ">")


class FTDV(vrnetlab.VR):
    def __init__(self, hostname, username, password, nics, conn_mode):
        super(FTDV, self).__init__(username, password)
        self.vms = [FTDV_vm(hostname, username, password, nics, conn_mode)]


class FTDV_installer(FTDV):
    """FTDV installer

    Will start the FTDv and perform initial bootstrapping to reduce boot time of the final image.
    """

    def __init__(self, hostname, username, password, nics, conn_mode):
        super(FTDV, self).__init__(username, password)
        self.vms = [
            FTDV_vm(
                hostname,
                username,
                password,
                nics,
                conn_mode,
                install_mode=True,
            )
        ]

    def install(self):
        self.logger.info("Installing FTDV")
        FTDV = self.vms[0]
        while not FTDV.running:
            FTDV.work()
        time.sleep(30)
        FTDV.stop()
        self.logger.info("Installation complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="admin", help="Username")
    parser.add_argument("--password", default="Admin@123", help="Password")
    parser.add_argument("--install", action="store_true", help="Install FTDv")
    parser.add_argument("--hostname", default="ftdv", help="Firewall Hostname")
    parser.add_argument("--nics", type=int, default=9, help="Number of NICS")
    parser.add_argument(
        "--connection-mode",
        default="tc",
        help="Connection mode to use in the datapath",
    )
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    if args.install:
        vr = FTDV_installer(
            args.hostname,
            args.username,
            args.password,
            args.nics,
            args.connection_mode,
        )
        vr.install()
    else:
        vr = FTDV(
            args.hostname,
            args.username,
            args.password,
            args.nics,
            args.connection_mode,
        )
        vr.start()
