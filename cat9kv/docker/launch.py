#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import subprocess
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


class cat9kv_vm(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode, vcpu, ram):
        disk_image = None
        for e in sorted(os.listdir("/")):
            if not disk_image and re.search(".qcow2$", e):
                disk_image = "/" + e
            if re.search(r"\.license$", e):
                os.rename("/" + e, "/tftpboot/license.lic")

        self.license = False
        if os.path.isfile("/tftpboot/license.lic"):
            logger.info("License found")
            self.license = True

        super().__init__(
            username,
            password,
            disk_image=disk_image,
            smp=f"cores={vcpu},threads=1,sockets=1",
            ram=ram,
            min_dp_nics=8,
        )
        self.hostname = hostname
        self.conn_mode = conn_mode
        self.num_nics = 9
        self.nic_type = "virtio-net-pci"

        self.image_name = "config.img"

        self.qemu_args.extend(
            [
                "-overcommit mem-lock=off",
                f"-boot order=cd -cdrom /{self.image_name}",
            ]
        )

        # create .img which is mounted for startup config and contains ASIC emulation in 'conf/vswitch.xml' dir.
        self.create_boot_image()

    def create_boot_image(self):
        """Creates a iso image with a bootstrap configuration"""
        try:
            os.makedirs("/img_dir/conf")
        except:
            self.logger.error(
                "Unable to make '/img_dir'. Does the directory already exist?"
            )

        try:
            os.popen("cp /vswitch.xml /img_dir/conf/")
        except:
            self.logger.debug("No vswitch.xml file provided.")

        with open("/img_dir/iosxe_config.txt", "w") as cfg_file:
            cfg_file.write(f"hostname {self.hostname}\r\n")
            cfg_file.write("end\r\n")

        genisoimage_args = [
            "genisoimage",
            "-l",
            "-o",
            "/" + self.image_name,
            "/img_dir",
        ]

        self.logger.debug("Generating boot ISO")
        subprocess.Popen(genisoimage_args)

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect(
            [
                b"Press RETURN to get started!",
                b"IOSXEBOOT-4-FACTORY_RESET",
            ],
            1,
        )
        if match:  # got a match!
            if ridx == 0:  # login
                self.logger.debug("matched, Press RETURN to get started.")

                self.wait_write("", wait=None)

                # run main config!
                self.bootstrap_config()
                # add startup config if present
                self.startup_config()
                # close telnet connection
                self.tn.close()
                # startup time?
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s", startup_time)
                # mark as running
                self.running = True
                return
            elif ridx == 1:  # IOSXEBOOT-4-FACTORY_RESET
                self.logger.warning("Unexpected reload while running")

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b"":
            self.logger.trace("OUTPUT: %s", res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return

    def bootstrap_config(self):
        """Do the actual bootstrap config"""
        self.logger.info("applying bootstrap configuration")

        self.wait_write("", None)
        self.wait_write("enable", wait=">")
        self.wait_write("configure terminal", wait=">")

        self.wait_write(f"hostname {self.hostname}")
        self.wait_write(
            "username %s privilege 15 password %s" % (self.username, self.password)
        )
        if int(self.version.split(".")[0]) >= 16:
            self.wait_write("ip domain name example.com")
        else:
            self.wait_write("ip domain-name example.com")
        self.wait_write("crypto key generate rsa modulus 2048")

        self.wait_write("no ip domain lookup")

        # add mgmt vrf static route
        self.wait_write("ip route vrf Mgmt-vrf 0.0.0.0 0.0.0.0 10.0.0.2")

        self.wait_write("interface GigabitEthernet0/0")
        self.wait_write("ip address 10.0.0.15 255.255.255.0")
        self.wait_write("no shut")
        self.wait_write("exit")

        self.wait_write("restconf")
        self.wait_write("netconf-yang")
        self.wait_write("netconf max-sessions 16")
        # I did not find any documentation about this, but is seems like a good idea!?
        self.wait_write("netconf detailed-error")
        self.wait_write("ip ssh server algorithm mac hmac-sha2-512")
        self.wait_write("ip ssh maxstartups 128")

        self.wait_write("line vty 0 4")
        self.wait_write("login local")
        self.wait_write("transport input all")
        self.wait_write("end")
        self.wait_write("copy running-config startup-config")
        self.wait_write("\r", "Destination")

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

        self.wait_write("configure terminal")
        # Apply lines from file
        for line in config_lines:
            self.wait_write(line)
        # End and Save
        self.wait_write("end")
        self.wait_write("copy running-config startup-config")
        self.wait_write("\r", "Destination")


class cat9kv(vrnetlab.VR):
    def __init__(self, hostname, username, password, conn_mode, vcpu, ram):
        super(cat9kv, self).__init__(username, password)
        self.vms = [cat9kv_vm(hostname, username, password, conn_mode, vcpu, ram)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
    parser.add_argument("--hostname", default="cat9kv", help="Router hostname")
    parser.add_argument(
        "--connection-mode",
        default="vrxcon",
        help="Connection mode to use in the datapath",
    )
    parser.add_argument("--vcpu", type=int, default=4, help="Allocated vCPUs")
    parser.add_argument("--ram", type=int, default=18432, help="Allocaetd RAM in MB")

    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)
    if args.trace:
        logger.setLevel(1)

    vr = cat9kv(
        args.hostname,
        args.username,
        args.password,
        args.connection_mode,
        args.vcpu,
        args.ram,
    )
    vr.start()
