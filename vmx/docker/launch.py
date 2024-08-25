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

STARTUP_CONFIG_FILE = "/config/startup-config.cfg"


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
    def __init__(
        self,
        hostname,
        username,
        password,
        image,
        conn_mode,
        install_mode=False,
    ):
        super(VMX_vcp, self).__init__(username, password, disk_image=image, ram=2048)
        self.hostname = hostname
        self.install_mode = install_mode
        self.num_nics = 0
        self.qemu_args.extend(["-drive", "if=ide,file=/vmx/re/vmxhdd.img"])
        self.smbios = [
            "type=0,vendor=Juniper",
            "type=1,manufacturer=VMX,product=VM-vcp_vmx2-161-re-0,version=0.1.0",
        ]
        # add metadata image if it exists
        if os.path.exists("/vmx/re/metadata-usb-re.img"):
            self.qemu_args.extend(
                [
                    "-usb",
                    "-drive",
                    "id=my_usb_disk,media=disk,format=raw,file=/vmx/re/metadata-usb-re.img,if=none",
                    "-device",
                    "usb-storage,drive=my_usb_disk",
                ]
            )
        self.conn_mode = conn_mode

    def start(self):
        # use parent class start() function
        super(VMX_vcp, self).start()
        # add interface to internal control plane bridge
        if not self.install_mode:
            vrnetlab.run_command(["brctl", "addif", "int_cp", "vcp-int"])
            vrnetlab.run_command(["ip", "link", "set", "vcp-int", "up"])

    def gen_mgmt(self):
        """Generate mgmt interface(s)

        We override the default function since we want a virtio NIC to the
        vFPC
        """
        # call parent function to generate first mgmt interface (e1000)
        res = super(VMX_vcp, self).gen_mgmt()
        if not self.install_mode:
            # add virtio NIC for internal control plane interface to vFPC
            res.append("-device")
            res.append("virtio-net-pci,netdev=vcp-int,mac=%s" % vrnetlab.gen_mac(1))
            res.append("-netdev")
            res.append("tap,ifname=vcp-int,id=vcp-int,script=no,downscript=no")
        return res

    def gen_nics(self):
        """
        Override the parent's gen_nic function,
        since dataplane interfaces are not to be created for VCP
        """
        return []

    def bootstrap_spin(self):
        """This function should be called periodically to do work.

        returns False when it has failed and given up, otherwise True
        """

        if self.spins > 300:
            # too many spins with no result -> restart
            self.logger.warning("no output from serial console, restarting VCP")
            self.stop()
            self.start()
            self.spins = 0
            return

        (ridx, match, res) = self.tn.expect([b"login:", b"root@(%|:~ #)"], 1)
        if match:  # got a match!
            if ridx == 0:  # matched login prompt, so should login
                self.logger.info("matched login prompt")
                self.wait_write("root", wait=None)
            if ridx == 1:
                if self.install_mode:
                    time.sleep(15)
                    self.wait_write(
                        "/usr/sbin/mgd -ZS intialsetup-commit ex_series_auto_config",
                        None,
                    )
                    time.sleep(15)
                    self.wait_write("cli")
                    self.wait_write("set cli screen-length 0", ">", 10)
                    self.wait_write("set cli screen-width 511", ">", 10)
                    self.wait_write("set cli complete-on-space off", ">", 10)
                    self.wait_write("edit exclusive", ">", 10)
                    self.wait_write("delete chassis auto-image-upgrade")
                    self.wait_write("commit")
                    self.wait_write("exit")
                    self.logger.info("requesting power-off")
                    self.wait_write("request system power-off", ">")
                    self.wait_write("yes", "Power Off the system")
                    self.running = True
                    return
                # run main config!
                self.bootstrap_config()
                self.startup_config()
                self.running = True
                self.tn.close()
                # calc startup time
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s" % startup_time)
                return

        else:
            # no match, if we saw some output from the router it's probably
            # booting, so let's give it some more time
            if res != b"":
                self.logger.trace("OUTPUT VCP: %s" % res.decode())
                # reset spins if we saw some output
                self.spins = 0

        self.spins += 1

    def bootstrap_config(self):
        """Do the actual bootstrap config"""
        self.wait_write("cli", None)
        self.wait_write("set cli screen-length 0", ">", 10)
        self.wait_write("set cli screen-width 511", ">", 10)
        self.wait_write("set cli complete-on-space off", ">", 10)
        self.wait_write("edit exclusive", ">", 10)
        self.wait_write("delete chassis auto-image-upgrade")
        self.wait_write("commit")
        self.wait_write("set chassis fpc 0 pic 0 number-of-ports 96")
        self.wait_write("set system host-name {}".format(self.hostname))
        self.wait_write("set system services ssh")
        self.wait_write("set system services netconf ssh")
        self.wait_write("set system services netconf rfc-compliant")
        self.wait_write(
            "set system services extension-service request-response grpc clear-text port 57400"
        )
        self.wait_write(
            "set system services extension-service request-response grpc max-connections 4"
        )
        self.wait_write(
            "set system login user %s class super-user authentication plain-text-password"
            % self.username
        )
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("set system root-authentication plain-text-password")
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("set interfaces fxp0 unit 0 family inet address 10.0.0.15/24")
        self.wait_write("delete interfaces fxp0 unit 0 family inet dhcp")
        self.wait_write("delete system processes dhcp-service")
        # set interface fxp0 on dedicated management vrf, to avoid 10.0.0.0/24 to overlap with any "testing" network
        self.wait_write("set system management-instance")
        self.wait_write(
            "set routing-instances mgmt_junos description management-instance"
        )
        # allow NATed outgoing traffic (set the default route on the management vrf)
        self.wait_write(
            "set routing-instances mgmt_junos routing-options static route 0.0.0.0/0 next-hop 10.0.0.2"
        )
        self.wait_write("commit")
        self.wait_write("exit")
        # write another exist as sometimes the first exit from exclusive edit abrupts before command finishes
        self.wait_write("exit", wait=">")

    def startup_config(self):
        """Load additional config provided by user."""

        if not os.path.exists(STARTUP_CONFIG_FILE):
            self.logger.trace(f"Startup config file {STARTUP_CONFIG_FILE} is not found")
            return

        self.logger.trace(f"Startup config file {STARTUP_CONFIG_FILE} exists")
        with open(STARTUP_CONFIG_FILE) as file:
            config_lines = file.readlines()
            config_lines = [line.rstrip() for line in config_lines]
            self.logger.trace(f"Parsed startup config file {STARTUP_CONFIG_FILE}")

        self.logger.info(f"Writing lines from {STARTUP_CONFIG_FILE}")

        self.wait_write("cli", "#", 10)
        self.wait_write("configure", ">", 10)
        # Apply lines from file
        for line in config_lines:
            self.wait_write(line)
        # Commit and GTFO
        self.wait_write("commit")
        self.wait_write("exit")

    def wait_write(self, cmd, wait="#", timeout=None):
        """Wait for something and then send command"""
        if wait:
            self.logger.trace("Waiting for {} before writing {}".format(wait, cmd))
            while True:
                (ridx, match, res) = self.tn.expect(
                    [wait.encode(), b"Retry connection attempts"], timeout=timeout
                )
                if match:
                    if ridx == 0:
                        break
                    if ridx == 1:
                        self.tn.write("yes\r".encode())
            self.logger.trace("Read: %s" % res.decode())
        self.logger.debug("writing to serial console: %s" % cmd)
        self.tn.write("{}\r".format(cmd).encode())


class VMX_vfpc(vrnetlab.VM):
    def __init__(self, version, conn_mode):
        super(VMX_vfpc, self).__init__(
            None, None, disk_image="/vmx/vfpc.img", num=1, cpu="SandyBridge", smp="3"
        )
        self.junos_version = version
        self.num_nics = 96

        self.nic_type = "virtio-net-pci"
        self.qemu_args.extend(["-M", "pc"])
        # add metadata image if it exists
        if os.path.exists("/vmx/metadata-usb-fpc0.img"):
            self.qemu_args.extend(
                [
                    "-usb",
                    "-drive",
                    "id=fpc_usb_disk,media=disk,format=raw,file=/vmx/metadata-usb-fpc0.img,if=none",
                    "-device",
                    "usb-storage,drive=fpc_usb_disk",
                ]
            )
        self.conn_mode = conn_mode

    def gen_mgmt(self):
        res = []
        # mgmt interface
        res.extend(
            ["-device", "virtio-net-pci,netdev=mgmt,mac=%s" % vrnetlab.gen_mac(0)]
        )
        res.extend(["-netdev", "user,id=mgmt,net=10.0.0.0/24"])
        # internal control plane interface to vFPC
        res.extend(
            ["-device", "virtio-net-pci,netdev=vfpc-int,mac=%s" % vrnetlab.gen_mac(0)]
        )
        res.extend(
            ["-netdev", "tap,ifname=vfpc-int,id=vfpc-int,script=no,downscript=no"]
        )

        if self.junos_version not in ("vmx-14.1R6.4"):
            # dummy interface for some vMX versions - not sure why vFPC wants
            # it but without it we get a misalignment
            res.extend(
                ["-device", "virtio-net-pci,netdev=dummy,mac=%s" % vrnetlab.gen_mac(0)]
            )
            res.extend(
                ["-netdev", "tap,ifname=vfpc-dummy,id=dummy,script=no,downscript=no"]
            )

        return res

    def start(self):
        # use parent class start() function
        super(VMX_vfpc, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(["brctl", "addif", "int_cp", "vfpc-int"])
        vrnetlab.run_command(["ip", "link", "set", "vfpc-int", "up"])

    def bootstrap_spin(self):
        (ridx, match, res) = self.tn.expect(
            [
                b"localhost login",
                b"qemux86-64 login",
                b"mounting /dev/sda2 on /mnt failed",
            ],
            1,
        )
        if match:
            if ridx == 0 or ridx == 1:  # got login - vFPC start succeeded!
                self.logger.info("vFPC successfully started")
                self.running = True
            if ridx == 2:  # vFPC start failed - restart it
                self.logger.info("vFPC start failed, restarting")
                self.stop()
                self.start()
        if res != b"":
            pass
            # self.logger.trace("OUTPUT VFPC: %s" % res.decode())

        return


class VMX(vrnetlab.VR):
    """Juniper vMX router"""

    def __init__(self, hostname, username, password, conn_mode):
        self.version = None
        self.version_info = []
        self.read_version()

        super(VMX, self).__init__(username, password)

        self.vms = [
            VMX_vcp(
                hostname,
                username,
                password,
                "/vmx/re/" + self.vcp_image,
                conn_mode=conn_mode,
            ),
            VMX_vfpc(self.version, conn_mode=conn_mode),
        ]

        # set up bridge for connecting VCP with vFPC
        vrnetlab.run_command(["brctl", "addbr", "int_cp"])
        vrnetlab.run_command(["ip", "link", "set", "int_cp", "up"])

    def read_version(self):
        for e in os.listdir("/vmx/re"):
            m = re.search(
                r"-(([0-9][0-9])\.([0-9])([A-Z])([0-9]+)(\-[SD][0-9]*)?\.([0-9]+))", e
            )
            if m:
                self.vcp_image = e
                self.version = m.group(1)
                self.version_info = [
                    int(m.group(2)),
                    int(m.group(3)),
                    m.group(4),
                    int(m.group(5)),
                    int(m.group(7)),
                ]


class VMX_installer(VMX):
    """VMX installer

    Will start the VMX VCP and then shut it down. Booting the VCP for the
    first time requires the VCP itself to load some config and then it will
    restart. Subsequent boots will not require this restart. By running
    this "install" when building the docker image we can decrease the
    normal startup time of the vMX.
    """

    def __init__(self, username, password, conn_mode):
        self.version = None
        self.version_info = []
        self.read_version()

        super(VMX, self).__init__(username, password)

        self.vms = [
            VMX_vcp(
                "install",
                username,
                password,
                "/vmx/re/" + self.vcp_image,
                install_mode=True,
                conn_mode=conn_mode,
            )
        ]

    def install(self):
        self.logger.info("Installing VMX")
        vcp = self.vms[0]
        while not vcp.running:
            vcp.work()

        # wait for system to shut down cleanly
        for i in range(0, 600):
            time.sleep(1)
            try:
                vcp.p.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            except Exception as exc:
                # assume it's dead
                self.logger.info(
                    "Can't communicate with qemu process, assuming VM has shut down properly."
                    + str(exc)
                )
                break

            try:
                (ridx, match, res) = vcp.tn.expect([b"Powering system off"], 1)
                if res != b"":
                    self.logger.trace("OUTPUT VCP: %s" % res.decode())
            except Exception as exc:
                # assume it's dead
                self.logger.info(
                    "Can't communicate over serial console, assuming VM has shut down properly."
                    + str(exc)
                )
                break

        vcp.stop()
        self.logger.info("Installation complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--hostname", default="vr-vmx", help="Router hostname")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
    parser.add_argument("--install", action="store_true", help="Install vMX")
    parser.add_argument(
        "--connection-mode",
        default="vrxcon",
        help="Connection mode to use in the datapath",
    )
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    logger.debug(
        "acting flags: username '{}', password '{}', install '{}', connection-mode '{}'".format(
            args.username, args.password, args.install, args.connection_mode
        )
    )

    logger.debug(f"Environment variables: {os.environ}")

    if args.install:
        vr = VMX_installer(args.username, args.password, conn_mode=args.connection_mode)
        vr.install()
    else:
        vrnetlab.boot_delay()
        vr = VMX(
            args.hostname, args.username, args.password, conn_mode=args.connection_mode
        )
        vr.start()
