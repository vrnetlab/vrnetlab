#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import sys

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


class VQFX_vcp(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode, version, disk_image):
        super(VQFX_vcp, self).__init__(
            username, password, disk_image=disk_image, ram=2048
        )
        self.num_nics = 12
        self.conn_mode = conn_mode
        self.hostname = hostname
        # _version is a custom version dict that has major and minor version components
        # while the self.version is a version @property of the common.VM class that reads
        # the value from the env var.
        self._version = version

    def start(self):
        # use parent class start() function
        super(VQFX_vcp, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(["brctl", "addif", "int_cp", "vcp-int"])
        vrnetlab.run_command(["ip", "link", "set", "vcp-int", "up"])

    def gen_mgmt(self):
        """Generate mgmt interface(s)

        We override the default function since we want a virtio NIC to the
        vFPC
        """
        # call parent function to generate first mgmt interface (e1000)
        res = super(VQFX_vcp, self).gen_mgmt()
        # add virtio NIC for internal control plane interface to vFPC
        res.append("-device")
        res.append("e1000,netdev=vcp-int,mac=%s" % vrnetlab.gen_mac(1))
        res.append("-netdev")
        res.append("tap,ifname=vcp-int,id=vcp-int,script=no,downscript=no")

        # dummy
        for i in range(1):
            res.append("-device")
            res.append("e1000,netdev=dummy%d,mac=%s" % (i, vrnetlab.gen_mac(1)))
            res.append("-netdev")
            res.append("tap,ifname=dummy%d,id=dummy%d,script=no,downscript=no" % (i, i))

        return res

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

        # logged_in_prompt prompt for v20+ versions
        logged_in_prompt = b"root@:RE:0%"

        if self._version["major"] < 20:
            logged_in_prompt = b"root@vqfx-re:RE:0%"

        (ridx, match, res) = self.tn.expect([b"login:", logged_in_prompt], 1)
        if match:  # got a match!
            if ridx == 0:  # matched login prompt, so should login
                self.logger.info("matched login prompt")
                self.wait_write("root", wait=None)

                # v19 has Juniper password for root login
                if self._version["major"] < 20:
                    self.wait_write("Juniper", wait="Password:")
            if ridx == 1:
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
        self.wait_write("configure", ">", 10)
        self.wait_write("set system services ssh")
        self.wait_write("set system services netconf ssh")
        self.wait_write("set system services netconf rfc-compliant")
        self.wait_write("delete system login user vagrant")
        self.wait_write(
            "set system login user %s class super-user authentication plain-text-password"
            % self.username
        )
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("set system root-authentication plain-text-password")
        self.wait_write(self.password, "New password:")
        self.wait_write(self.password, "Retype new password:")
        self.wait_write("delete interfaces")
        self.wait_write("set interfaces em0 unit 0 family inet address 10.0.0.15/24")
        self.wait_write("set interfaces em1 unit 0 family inet address 169.254.0.2/24")
        self.wait_write(f"set system host-name {self.hostname}")
        self.wait_write("commit")
        self.wait_write("exit")

    def startup_config(self):
        """Load additional config provided by user."""

        if os.path.exists(STARTUP_CONFIG_FILE):
            self.logger.trace("Config File %s exists" % STARTUP_CONFIG_FILE)
            with open(STARTUP_CONFIG_FILE) as file:
                self.logger.trace("Opening Config File %s" % STARTUP_CONFIG_FILE)
                config_lines = file.readlines()
                config_lines = [line.rstrip() for line in config_lines]
                self.logger.trace("Parsed Config File %s" % STARTUP_CONFIG_FILE)

            self.logger.info("Writing lines from %s" % STARTUP_CONFIG_FILE)
            # Enter Config Mode on QFX
            self.wait_write("cli", None)
            self.wait_write("configure", ">", 10)
            # Appline lines from file
            for line in config_lines:
                self.wait_write(line)
            # Commit and GTFO
            self.wait_write("commit")
            self.wait_write("exit")

            self.logger.info("Done loading config file %s" % STARTUP_CONFIG_FILE)

    def wait_write(self, cmd, wait="#", timeout=None):
        """Wait for something and then send command"""
        if wait:
            self.logger.trace("Waiting for %s" % wait)
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


class VQFX_vpfe(vrnetlab.VM):
    def __init__(self, disk_image):
        super(VQFX_vpfe, self).__init__(
            None, None, disk_image=disk_image, num=1, ram=2048
        )
        self.num_nics = 0

    def gen_mgmt(self):
        res = []
        # mgmt interface
        res.extend(["-device", "e1000,netdev=mgmt,mac=%s" % vrnetlab.gen_mac(0)])
        res.extend(["-netdev", "user,id=mgmt,net=10.0.0.0/24"])
        # internal control plane interface to vFPC
        res.extend(["-device", "e1000,netdev=vpfe-int,mac=%s" % vrnetlab.gen_mac(0)])
        res.extend(
            ["-netdev", "tap,ifname=vpfe-int,id=vpfe-int,script=no,downscript=no"]
        )

        return res

    def start(self):
        # use parent class start() function
        super(VQFX_vpfe, self).start()
        # add interface to internal control plane bridge
        vrnetlab.run_command(["brctl", "addif", "int_cp", "vpfe-int"])
        vrnetlab.run_command(["ip", "link", "set", "vpfe-int", "up"])

    def gen_nics(self):
        """
        Override the parent's gen_nic function,
        since dataplane interfaces are not to be created for VCP
        """
        return []

    def bootstrap_spin(self):
        self.running = True
        self.tn.close()
        return


class VQFX(vrnetlab.VR):
    """Juniper vQFX router"""

    def __init__(self, hostname, username, password, conn_mode):
        super(VQFX, self).__init__(username, password)

        self.read_version()

        self.vms = [
            VQFX_vcp(
                hostname, username, password, conn_mode, self.ver, self.vcp_qcow_name
            ),
            VQFX_vpfe(self.pfe_qcow_name),
        ]

        # set up bridge for connecting VCP with vFPC
        vrnetlab.run_command(["brctl", "addbr", "int_cp"])
        vrnetlab.run_command(["ip", "link", "set", "int_cp", "up"])

    def read_version(self):
        for e in os.listdir("/"):
            vcp_match = re.match(r"vqfx-(\d+)\.(\w+)\.(\w+)\S+re\S+\.qcow2", e)
            if vcp_match:
                self.ver = {
                    "major": int(vcp_match.group(1)),
                    "minor": vcp_match.group(2),
                }
                self.vcp_qcow_name = vcp_match.group(0)

            # https://regex101.com/r/4ByEhT/1
            pfe_match = re.match(r"vqfx-(\d+)\.(\w+)\S+-pfe.+qcow2?", e)
            if pfe_match:
                self.pfe_qcow_name = pfe_match.group(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--hostname", default="vr-vqfx", help="QFX hostname")
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
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
    vrnetlab.boot_delay()
    vr = VQFX(
        args.hostname, args.username, args.password, conn_mode=args.connection_mode
    )
    vr.start()
