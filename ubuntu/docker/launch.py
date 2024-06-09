#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import subprocess
import sys

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


class Ubuntu_vm(vrnetlab.VM):
    def __init__(
        self,
        hostname,
        username,
        password,
        nics,
        conn_mode,
    ):
        for e in os.listdir("/"):
            if re.search(".qcow2$", e):
                disk_image = "/" + e

        super(Ubuntu_vm, self).__init__(
            username, password, disk_image=disk_image, ram=512
        )

        self.num_nics = nics
        self.hostname = hostname
        self.conn_mode = conn_mode
        self.nic_type = "virtio-net-pci"

        self.image_name = "cloud_init.iso"
        self.create_boot_image()

        self.qemu_args.extend(["-cdrom", "/" + self.image_name])

        if "ADD_DISK" in os.environ:
            disk_size = os.getenv("ADD_DISK")

            self.add_disk(disk_size)

    def create_boot_image(self):
        """Creates a cloud-init iso image with a bootstrap configuration"""

        with open("/bootstrap_config.yaml", "w") as cfg_file:
            cfg_file.write("#cloud-config\n")
            cfg_file.write(f"hostname: {self.hostname}\n")
            cfg_file.write(f"fqdn: {self.hostname}\n")
            cfg_file.write("users:\n")
            cfg_file.write(f"  - name: {self.username}\n")
            cfg_file.write("    shell: /bin/bash\n")
            cfg_file.write('    sudo: "ALL=(ALL) NOPASSWD: ALL"\n')
            cfg_file.write("    groups: users, admin\n")
            cfg_file.write(f"    plain_text_passwd: {self.password}\n")
            cfg_file.write("    lock_passwd: false\n")
            cfg_file.write("ssh_pwauth: true\n")
            cfg_file.write("disable_root: false\n")
            cfg_file.write("timezone: Europe/Berlin\n")
            # Disable cloud-init for the subsequent boots
            cfg_file.write("runcmd:\n")
            cfg_file.write("  - touch /etc/cloud/cloud-init.disabled\n")

        with open("/network_config.yaml", "w") as net_cfg_file:
            net_cfg_file.write("version: 2\n")
            net_cfg_file.write("ethernets:\n")
            net_cfg_file.write("  enp1s0:\n")
            net_cfg_file.write("    addresses: [10.0.0.15/24]\n")
            net_cfg_file.write("    gateway4: 10.0.0.2\n")
            net_cfg_file.write("    nameservers:\n")
            net_cfg_file.write("        addresses: [ 9.9.9.9 ]\n")

        cloud_localds_args = [
            "cloud-localds",
            "-v",
            "--network-config=/network_config.yaml",
            "/" + self.image_name,
            "/bootstrap_config.yaml",
        ]

        subprocess.Popen(cloud_localds_args)

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 6000:
            # too many spins with no result ->  give up
            self.logger.debug("Too many spins -> give up")
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"login: "], 1)
        if match:  # got a match!
            if ridx == 0:  # login
                self.logger.debug("matched, login: ")
                self.wait_write("", wait=None)

                self.running = True
                # close telnet connection
                self.tn.close()
                # startup time?
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s", startup_time)
                return

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b"":
            self.logger.trace("OUTPUT: %s" % res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return

    def gen_mgmt(self):
        """
        Augment the parent class function to change the PCI bus
        """
        # call parent function to generate the mgmt interface
        res = super(Ubuntu_vm, self).gen_mgmt()

        # we need to place mgmt interface on the same bus with other interfaces in Ubuntu,
        # to get nice (predictable) interface names
        if "bus=pci.1" not in res[-3]:
            res[-3] = res[-3] + ",bus=pci.1"
        return res

    def add_disk(self, disk_size, driveif="ide"):
        additional_disk = f"disk_{disk_size}.qcow2"

        if not os.path.exists(additional_disk):
            self.logger.debug(f"Creating additional disk image {additional_disk}")
            vrnetlab.run_command(
                ["qemu-img", "create", "-f", "qcow2", additional_disk, disk_size]
            )

        self.qemu_args.extend(
            [
                "-drive",
                f"if={driveif},file={additional_disk}",
            ]
        )


class Ubuntu(vrnetlab.VR):
    def __init__(self, hostname, username, password, nics, conn_mode):
        super(Ubuntu, self).__init__(username, password)
        self.vms = [Ubuntu_vm(hostname, username, password, nics, conn_mode)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="sysadmin", help="Username")
    parser.add_argument("--password", default="sysadmin", help="Password")
    parser.add_argument("--hostname", default="ubuntu", help="VM Hostname")
    parser.add_argument("--nics", type=int, default=16, help="Number of NICS")
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

    vr = Ubuntu(
        args.hostname,
        args.username,
        args.password,
        args.nics,
        args.connection_mode,
    )
    vr.start()
