#!/usr/bin/env python3

import datetime
import json
import logging
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys

import vrnetlab
import yaml

DEFAULT_IFCFG_ETH0 = """
DEVICE=eth0
BOOTPROTO=none
ONBOOT=yes
NETMASK=255.255.255.0
IPADDR=10.0.0.15
GATEWAY=10.0.0.2
DNS1=9.9.9.9
USERCTL=yes
"""

CONFIG_DRIVE = os.path.join("/", "config_drive")
ISO_DRIVE = os.path.join("/", "iso_drive")


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


class CmgLinux_vm(vrnetlab.VM):
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

        super(CmgLinux_vm, self).__init__(
            username, password, disk_image=disk_image, ram=6144, smp="4"
        )

        self.num_nics = nics
        self.hostname = hostname
        self.conn_mode = conn_mode
        self.nic_type = "virtio-net-pci"

        self.cfg_drive_iso_path = os.path.join("/", "iso-drive.iso")
        self.create_config_drive_image()

        self.qemu_args.extend(["-cdrom", self.cfg_drive_iso_path])

        if "ADD_DISK" in os.environ:
            disk_size = os.getenv("ADD_DISK")

            self.add_disk(disk_size)

    def _update_user_data(self, user_data: dict) -> dict:
        if "users" not in user_data:
            user_data["users"] = []

        clab_user = [u for u in user_data["users"] if u.get("name") == self.username]
        # Just update if the user not exist
        # If exists the the user may have another intention
        # to configure the user
        if not clab_user:
            user_data["users"].append(
                {
                    "name": self.username,
                    "plain_text_passwd": self.password,
                    "lock_passwd": False,
                    "sudo": "ALL=(ALL) NOPASSWD:ALL",
                }
            )

        if "write_files" not in user_data:
            user_data["write_files"] = []

        ifcfg = [
            p
            for p in user_data["write_files"]
            if p.get("path") == "/etc/sysconfig/network-scripts/ifcfg-eth0"
        ]
        if not ifcfg:
            user_data["write_files"].append(
                {
                    "path": "/etc/sysconfig/network-scripts/ifcfg-eth0",
                    "content": DEFAULT_IFCFG_ETH0,
                }
            )
        else:
            ifcfg_eth0 = ifcfg[0]
            ifcfg_eth0["content"] = DEFAULT_IFCFG_ETH0

        return user_data

    @staticmethod
    def _update_meta_data(meta_data: dict) -> dict:
        if "uuid" not in meta_data:
            meta_data["uuid"] = "00000000-0000-0000-0000-000000000000"

        node_name = os.environ.get("CLAB_LABEL_CLAB_NODE_NAME", "cmg-linux")
        meta_data["hostname"] = node_name
        meta_data["name"] = node_name

        return meta_data

    def create_config_drive_image(self):
        iso_latest_dir = os.path.join(ISO_DRIVE, "openstack", "latest")
        user_data_path = os.path.join(iso_latest_dir, "user_data")
        meta_data_path = os.path.join(iso_latest_dir, "meta_data.json")

        if not os.path.isdir(iso_latest_dir):
            os.makedirs(iso_latest_dir, exist_ok=True)

        config_dir_latest = os.path.join(CONFIG_DRIVE, "openstack", "latest")
        if os.path.isdir(config_dir_latest):
            shutil.copytree(config_dir_latest, iso_latest_dir, dirs_exist_ok=True)

        config_dir_content = os.path.join(CONFIG_DRIVE, "openstack", "content")
        if os.path.isdir(config_dir_content):
            shutil.copytree(
                config_dir_content,
                os.path.join(ISO_DRIVE, "openstack", "content"),
                dirs_exist_ok=True,
            )

        # Update user_data
        user_data = {}
        if os.path.isfile(user_data_path):
            with open(user_data_path, "r") as f:
                user_data = yaml.safe_load(f)
        else:
            user_data = {
                "users": [],
                "write_files": [],
                "final_message": "Vrnetlab cloud init done",
            }

        # Dump updated user_data to the original file
        user_data = self._update_user_data(user_data)
        with open(user_data_path, "w") as f:
            ctx_str = yaml.safe_dump(user_data, sort_keys=False, indent=2)
            ctx_str = f"#cloud-config\n{ctx_str}"
            f.write(ctx_str)

        # Update meta_data.json
        meta_data = {}
        if os.path.isfile(meta_data_path):
            with open(meta_data_path, "r") as f:
                meta_data = yaml.safe_load(f)

        # Dump updated meta_data to the original file
        meta_data = self._update_meta_data(meta_data)
        with open(meta_data_path, "w") as f:
            json.dump(meta_data, f, indent=2)

        # Create seeds.iso or config_drive.iso
        cmd_args = shlex.split(
            f"mkisofs -J -l -R -V config-2 -iso-level 4 -o {self.cfg_drive_iso_path} /iso_drive"
        )
        subprocess.Popen(cmd_args)

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 6000:
            # too many spins with no result ->  give up
            self.logger.debug("Too many spins -> give up")
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"login: "], 1)
        # got am match and login
        if match and ridx == 0:
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
        res = super(CmgLinux_vm, self).gen_mgmt()

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


class CmgLinux(vrnetlab.VR):
    def __init__(self, hostname, username, password, nics, conn_mode):
        super(CmgLinux, self).__init__(username, password)
        self.vms = [CmgLinux_vm(hostname, username, password, nics, conn_mode)]


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

    vr = CmgLinux(
        args.hostname,
        args.username,
        args.password,
        args.nics,
        args.connection_mode,
    )
    vr.start()
