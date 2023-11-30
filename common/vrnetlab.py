#!/usr/bin/env python3

import datetime
import json
import logging
import math
import os
import random
import re
import subprocess
import telnetlib
import time
import sys
from pathlib import Path

MAX_RETRIES = 60


def gen_mac(last_octet=None):
    """Generate a random MAC address that is in recognizable (0C:00) OUI space
    and that has the given last octet.
    """
    return "0C:00:%02x:%02x:%02x:%02x" % (
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
        last_octet,
    )


# sorting function to naturally sort interfaces by names
def natural_sort_key(s, _nsre=re.compile("([0-9]+)")):
    return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(s)]


def run_command(cmd, cwd=None, background=False, shell=False):
    res = None
    try:
        if background:
            p = subprocess.Popen(cmd, cwd=cwd, shell=shell)
        else:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd, shell=shell)
            res = p.communicate()
    except:
        pass
    return res


# boot_delay delays the VM boot by number of seconds
# set by BOOT_DELAY env var
def boot_delay():
    delay = os.getenv("BOOT_DELAY")
    if delay and (delay != "" or delay != 0):
        logging.getLogger().info(f"Delaying VM boot of by {delay} seconds")
        time.sleep(int(delay))


class VM:
    def __str__(self):
        return self.__class__.__name__

    def _overlay_disk_image_format(self) -> str:
        res = run_command(["qemu-img", "info", "--output", "json", self.image])
        if res is not None:
            image_info = json.loads(res[0])
            if "format" in image_info:
                return image_info["format"]
        raise ValueError(f"Could not read image format for {self.image}")

    def __init__(self, username, password, disk_image=None, num=0, ram=4096):
        self.logger = logging.getLogger()

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
        # number of nics that are actually *provisioned* (as in nics that will be added to container)
        self.num_provisioned_nics = int(os.environ.get("CLAB_INTFS", 0))
        # "highest" provisioned nic num -- used for making sure we can allocate nics without needing
        # to have them allocated sequential from eth1
        self.highest_provisioned_nic_num = 0

        self.nics_per_pci_bus = 26  # tested to work with XRv
        self.smbios = []

        self.start_nic_eth_idx = 1

        # wait_pattern is the pattern we wait on the serial connection when pushing config commands
        self.wait_pattern = "#"

        overlay_disk_image = re.sub(r"(\.[^.]+$)", r"-overlay\1", disk_image)
        # append role to overlay name to have different overlay images for control and data plane images
        if hasattr(self, "role"):
            tokens = overlay_disk_image.split(".")
            tokens[0] = tokens[0] + "-" + self.role + str(self.num)
            overlay_disk_image = ".".join(tokens)

        if not os.path.exists(overlay_disk_image):
            self.logger.debug("Creating overlay disk image")
            run_command(
                [
                    "qemu-img",
                    "create",
                    "-f",
                    "qcow2",
                    "-F",
                    self._overlay_disk_image_format(),
                    "-b",
                    disk_image,
                    overlay_disk_image,
                ]
            )

        self.qemu_args = ["qemu-system-x86_64", "-display", "none", "-machine", "pc"]
        self.qemu_args.extend(
            ["-monitor", "tcp:0.0.0.0:40%02d,server,nowait" % self.num]
        )
        self.qemu_args.extend(
            [
                "-m",
                str(ram),
                "-serial",
                "telnet:0.0.0.0:50%02d,server,nowait" % self.num,
                "-drive",
                "if=ide,file=%s" % overlay_disk_image,
            ]
        )
        # enable hardware assist if KVM is available
        if os.path.exists("/dev/kvm"):
            self.qemu_args.insert(1, "-enable-kvm")

    def start(self):
        self.logger.info("Starting %s" % self.__class__.__name__)
        self.start_time = datetime.datetime.now()

        cmd = list(self.qemu_args)

        # uuid
        if self.uuid:
            cmd.extend(["-uuid", self.uuid])

        # do we have a fake start date?
        if self.fake_start_date:
            cmd.extend(["-rtc", "base=" + self.fake_start_date])

        # smbios
        # adding quotes to smbios value so it can be processed by bash shell
        for smbios_line in self.smbios:
            quoted_smbios = '"' + smbios_line + '"'
            cmd.extend(["-smbios", quoted_smbios])

        # setup PCI buses
        for i in range(1, math.ceil(self.num_nics / self.nics_per_pci_bus) + 1):
            cmd.extend(["-device", "pci-bridge,chassis_nr={},id=pci.{}".format(i, i)])

        # generate mgmt NICs
        cmd.extend(self.gen_mgmt())
        # generate normal NICs
        cmd.extend(self.gen_nics())

        self.logger.debug("qemu cmd: {}".format(" ".join(cmd)))

        self.p = subprocess.Popen(
            " ".join(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True,
            executable="/bin/bash",
        )

        try:
            outs, errs = self.p.communicate(timeout=2)
            self.logger.info("STDOUT: %s" % outs)
            self.logger.info("STDERR: %s" % errs)
        except:
            pass

        for i in range(1, MAX_RETRIES + 1):
            try:
                self.qm = telnetlib.Telnet("127.0.0.1", 4000 + self.num)
                break
            except:
                self.logger.info(
                    "Unable to connect to qemu monitor (port {}), retrying in a second (attempt {})".format(
                        4000 + self.num, i
                    )
                )
                time.sleep(1)
            if i == MAX_RETRIES:
                raise QemuBroken(
                    "Unable to connect to qemu monitor on port {}".format(
                        4000 + self.num
                    )
                )

        for i in range(1, MAX_RETRIES + 1):
            try:
                self.tn = telnetlib.Telnet("127.0.0.1", 5000 + self.num)
                break
            except:
                self.logger.info(
                    "Unable to connect to qemu monitor (port {}), retrying in a second (attempt {})".format(
                        5000 + self.num, i
                    )
                )
                time.sleep(1)
            if i == MAX_RETRIES:
                raise QemuBroken(
                    "Unable to connect to qemu monitor on port {}".format(
                        5000 + self.num
                    )
                )
        try:
            outs, errs = self.p.communicate(timeout=2)
            self.logger.info("STDOUT: %s" % outs)
            self.logger.info("STDERR: %s" % errs)
        except:
            pass

    def create_bridges(self):
        """Create a linux bridge for every attached eth interface
        Returns list of bridge names
        """
        # based on https://github.com/plajjan/vrnetlab/pull/188
        run_command(["mkdir", "-p", "/etc/qemu"])  # This is to whitlist all bridges
        run_command(["echo 'allow all' > /etc/qemu/bridge.conf"], shell=True)

        bridges = list()
        intfs = [x for x in os.listdir("/sys/class/net/") if "eth" in x if x != "eth0"]
        intfs.sort(key=natural_sort_key)

        self.logger.info("Creating bridges for interfaces: %s" % intfs)

        for idx, intf in enumerate(intfs):
            run_command(
                ["ip", "link", "add", "name", "br-%s" % idx, "type", "bridge"],
                background=True,
            )
            run_command(["ip", "link", "set", "br-%s" % idx, "up"])
            run_command(["ip", "link", "set", intf, "mtu", "65000"])
            run_command(["ip", "link", "set", intf, "master", "br-%s" % idx])
            run_command(
                ["echo 16384 > /sys/class/net/br-%s/bridge/group_fwd_mask" % idx],
                shell=True,
            )
            bridges.append("br-%s" % idx)
        return bridges

    def create_ovs_bridges(self):
        """Create a OvS bridges for every attached eth interface
        Returns list of bridge names
        """

        ifup_script = """#!/bin/sh

        switch="vr-ovs-$1"
        ip link set $1 up
        ip link set $1 mtu 65000
        ovs-vsctl add-port ${switch} $1"""

        with open("/etc/vr-ovs-ifup", "w") as f:
            f.write(ifup_script)
        os.chmod("/etc/vr-ovs-ifup", 0o777)

        # start ovs services
        # system-id doesn't mean anything here
        run_command(
            [
                "/usr/share/openvswitch/scripts/ovs-ctl",
                f"--system-id={random.randint(1000,50000)}",
                "start",
            ]
        )

        time.sleep(3)

        bridges = list()
        intfs = [x for x in os.listdir("/sys/class/net/") if "eth" in x if x != "eth0"]
        intfs.sort(key=natural_sort_key)

        self.logger.info("Creating ovs bridges for interfaces: %s" % intfs)

        for idx, intf in enumerate(intfs):
            brname = f"vr-ovs-tap{idx+1}"
            # generate a mac for ovs bridge, since this mac we will need
            # to create a "drop flow" rule to filter grARP replies we can't have
            # ref: https://mail.openvswitch.org/pipermail/ovs-discuss/2021-February/050951.html
            brmac = gen_mac(0)
            self.logger.debug(f"Creating bridge {brname} with {brmac} hw address")
            if self.conn_mode == "ovs":
                run_command(
                    f"ovs-vsctl add-br {brname} -- set bridge {brname} other-config:hwaddr={brmac}",
                    shell=True,
                )
            if self.conn_mode == "ovs-user":
                run_command(
                    f"ovs-vsctl add-br {brname}",
                    shell=True,
                )
                run_command(
                    f"ovs-vsctl set bridge {brname} datapath_type=netdev",
                    shell=True,
                )
                run_command(
                    f"ovs-vsctl set bridge {brname} other-config:hwaddr={brmac}",
                    shell=True,
                )
            run_command(["ip", "link", "set", "dev", brname, "mtu", "9000"])
            run_command(
                [
                    "ovs-vsctl",
                    "set",
                    "bridge",
                    brname,
                    "other-config:forward-bpdu=true",
                ]
            )
            run_command(["ovs-vsctl", "add-port", brname, intf])
            run_command(["ip", "link", "set", "dev", brname, "up"])
            run_command(
                [
                    "ovs-ofctl",
                    "add-flow",
                    brname,
                    f"table=0,arp,dl_src={brmac} actions=drop",
                ]
            )
            bridges.append(brname)
        return bridges

    def create_tc_tap_ifup(self):
        """Create tap ifup script that is used in tc datapath mode"""
        ifup_script = """#!/bin/bash

        TAP_IF=$1
        # get interface index number up to 3 digits (everything after first three chars)
        # tap0 -> 0
        # tap123 -> 123
        INDEX=${TAP_IF:3:3}

        ip link set $TAP_IF up
        ip link set $TAP_IF mtu 65000

        # create tc eth<->tap redirect rules
        tc qdisc add dev eth$INDEX ingress
        tc filter add dev eth$INDEX parent ffff: protocol all u32 match u8 0 0 action mirred egress redirect dev tap$INDEX

        tc qdisc add dev $TAP_IF ingress
        tc filter add dev $TAP_IF parent ffff: protocol all u32 match u8 0 0 action mirred egress redirect dev eth$INDEX
        """

        with open("/etc/tc-tap-ifup", "w") as f:
            f.write(ifup_script)
        os.chmod("/etc/tc-tap-ifup", 0o777)

    def create_macvtaps(self):
        """
        Create Macvtap interfaces for each non dataplane interface
        """
        intfs = [x for x in os.listdir("/sys/class/net/") if "eth" in x if x != "eth0"]
        self.data_ifaces = intfs
        intfs.sort(key=natural_sort_key)

        for idx, intf in enumerate(intfs):
            self.logger.debug("Creating macvtap interfaces for link: %s" % intf)
            run_command(
                [
                    "ip",
                    "link",
                    "add",
                    "link",
                    intf,
                    "name",
                    "macvtap{}".format(idx + 1),
                    "type",
                    "macvtap",
                    "mode",
                    "passthru",
                ],
            )
            run_command(
                [
                    "ip",
                    "link",
                    "set",
                    "dev",
                    "macvtap{}".format(idx + 1),
                    "up",
                ],
            )

    def gen_mgmt(self):
        """Generate qemu args for the mgmt interface(s)"""
        res = []
        # mgmt interface is special - we use qemu user mode network
        res.append("-device")
        res.append(self.nic_type + f",netdev=p00,mac={gen_mac(0)}")
        res.append("-netdev")
        res.append(
            "user,id=p00,net=10.0.0.0/24,"
            "tftp=/tftpboot,"
            "hostfwd=tcp::2022-10.0.0.15:22,"
            "hostfwd=udp::2161-10.0.0.15:161,"
            "hostfwd=tcp::2830-10.0.0.15:830,"
            "hostfwd=tcp::2080-10.0.0.15:80,"
            "hostfwd=tcp::2443-10.0.0.15:443"
        )
        return res

    def nic_provision_delay(self) -> None:
        self.logger.debug(
            f"number of provisioned data plane interfaces is {self.num_provisioned_nics}"
        )

        if self.num_provisioned_nics == 0:
            # no nics provisioned and/or not running from containerlab so we can bail
            return

        self.logger.debug("waiting for provisioned interfaces to appear...")

        # start_eth means eth index for VM
        # particularly for multiple slot LC
        start_eth = self.start_nic_eth_idx
        end_eth = self.start_nic_eth_idx + self.num_nics

        inf_path = Path("/sys/class/net/")
        while True:
            provisioned_nics = list(inf_path.glob("eth*"))
            # if we see num provisioned +1 (for mgmt) we have all nics ready to roll!
            if len(provisioned_nics) >= self.num_provisioned_nics + 1:
                nics = [
                    int(re.search(pattern=r"\d+", string=nic.name).group())
                    for nic in provisioned_nics
                ]

                # Ensure the max eth is in range of allocated eth index of VM LC
                nics = [nic for nic in nics if nic in range(start_eth, end_eth)]

                if nics:
                    self.highest_provisioned_nic_num = max(nics)

                self.logger.debug(
                    f"highest allocated interface id determined to be: {self.highest_provisioned_nic_num}..."
                )
                self.logger.debug("interfaces provisioned, continuing...")
                return
            time.sleep(5)

    def gen_nics(self):
        """Generate qemu args for the normal traffic carrying interface(s)"""
        self.nic_provision_delay()

        res = []
        bridges = []

        if self.conn_mode == "tc":
            self.create_tc_tap_ifup()
        elif self.conn_mode in ["ovs", "ovs-user"]:
            bridges = self.create_ovs_bridges()
            if len(bridges) > self.num_nics:
                self.logger.error(
                    "Number of dataplane interfaces '{}' exceeds the requested number of links '{}'".format(
                        len(bridges), self.num_nics
                    )
                )
                sys.exit(1)
        elif self.conn_mode == "macvtap":
            self.create_macvtaps()
        elif self.conn_mode == "bridge":
            bridges = self.create_bridges()
            if len(bridges) > self.num_nics:
                self.logger.error(
                    "Number of dataplane interfaces '{}' exceeds the requested number of links '{}'".format(
                        len(bridges), self.num_nics
                    )
                )
                sys.exit(1)

        start_eth = self.start_nic_eth_idx
        end_eth = self.start_nic_eth_idx + self.num_nics
        pci_bus_ctr = 0
        for i in range(start_eth, end_eth):
            # PCI bus counter is to ensure pci bus index starts from 1
            # and continuing in sequence regardles the eth index
            pci_bus_ctr += 1

            # calc which PCI bus we are on and the local add on that PCI bus
            x = pci_bus_ctr
            if "vEOS" in self.image:
                x = pci_bus_ctr + 1

            pci_bus = math.floor(x / self.nics_per_pci_bus) + 1
            addr = (x % self.nics_per_pci_bus) + 1

            # if the matching container interface ethX doesn't exist, we don't create a nic
            if not os.path.exists(f"/sys/class/net/eth{i}"):
                if i >= self.highest_provisioned_nic_num:
                    continue

                # current intf number is *under* the highest provisioned nic number, so we need
                # to allocate a "dummy" interface so that when the users data plane interface is
                # actually provisioned it is provisioned in the appropriate "slot"
                res.extend(
                    [
                        "-device",
                        "%(nic_type)s,"
                        "netdev=p%(i)02d,"
                        "bus=pci.%(pci_bus)s,"
                        "addr=0x%(addr)x"
                        % {
                            "nic_type": self.nic_type,
                            "i": i,
                            "pci_bus": pci_bus,
                            "addr": addr,
                        },
                        "-netdev",
                        "socket,id=p%(i)02d,listen=:%(j)02d" % {"i": i, "j": i + 10000},
                    ]
                )
                continue

            mac = ""
            if self.conn_mode == "macvtap":
                # get macvtap interface mac that will be used in qemu nic config
                if not os.path.exists("/sys/class/net/macvtap{}/address".format(i)):
                    continue
                with open("/sys/class/net/macvtap%s/address" % i, "r") as f:
                    mac = f.readline().strip("\n")
            else:
                mac = gen_mac(i)

            res.append("-device")
            res.append(
                "%(nic_type)s,netdev=p%(i)02d,mac=%(mac)s,bus=pci.%(pci_bus)s,addr=0x%(addr)x"
                % {
                    "nic_type": self.nic_type,
                    "i": i,
                    "pci_bus": pci_bus,
                    "addr": addr,
                    "mac": mac,
                }
            )

            if self.conn_mode == "tc":
                res.append("-netdev")
                res.append(
                    f"tap,id=p{i:02d},ifname=tap{i},script=/etc/tc-tap-ifup,downscript=no"
                )

            if self.conn_mode == "macvtap":
                # if required number of nics exceeds the number of attached interfaces
                # we skip excessive ones
                if not os.path.exists("/sys/class/net/macvtap{}/ifindex".format(i)):
                    continue
                # init value of macvtap ifindex
                tapidx = 0
                with open("/sys/class/net/macvtap%s/ifindex" % i, "r") as f:
                    tapidx = f.readline().strip("\n")

                fd = 100 + i  # fd start number for tap iface
                vhfd = 400 + i  # vhost fd start number

                res.append("-netdev")
                res.append(
                    "tap,id=p%(i)02d,fd=%(fd)s,vhost=on,vhostfd=%(vhfd)s %(fd)s<>/dev/tap%(tapidx)s %(vhfd)s<>/dev/vhost-net"
                    % {"i": i, "fd": fd, "vhfd": vhfd, "tapidx": tapidx}
                )

            elif self.conn_mode == "bridge":
                if i <= len(bridges):
                    bridge = bridges[i - 1]  # We're starting from 0
                    res.append("-netdev")
                    res.append(
                        "bridge,id=p%(i)02d,br=%(bridge)s" % {"i": i, "bridge": bridge}
                    )
                else:  # We don't create more interfaces than we have bridges
                    del res[-2:]  # Removing recently added interface

            elif self.conn_mode in ["ovs", "ovs-user"]:
                if i <= len(bridges):
                    res.append("-netdev")
                    res.append(
                        "tap,id=p%(i)02d,ifname=tap%(i)s,script=/etc/vr-ovs-ifup,downscript=no"
                        % {"i": i}
                    )
                else:  # We don't create more interfaces than we have bridges
                    del res[-2:]  # Removing recently added interface

            elif self.conn_mode == "vrxcon":
                res.append("-netdev")
                res.append(
                    "socket,id=p%(i)02d,listen=:%(j)02d" % {"i": i, "j": i + 10000}
                )
        return res

    def stop(self):
        """Stop this VM"""
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
        """Restart this VM"""
        self.stop()
        self.start()

    def wait_write(self, cmd, wait="__defaultpattern__", con=None, clean_buffer=False):
        """Wait for something on the serial port and then send command

        Defaults to using self.tn as connection but this can be overridden
        by passing a telnetlib.Telnet object in the con argument.
        """
        con_name = "custom con"
        if con is None:
            con = self.tn

        if con == self.tn:
            con_name = "serial console"
        if con == self.qm:
            con_name = "qemu monitor"

        if wait:
            # use class default wait pattern if none was explicitly specified
            if wait == "__defaultpattern__":
                wait = self.wait_pattern
            self.logger.trace(f"waiting for '{wait}' on {con_name}")
            res = con.read_until(wait.encode())

            cleaned_buf = (
                (con.read_very_eager()) if clean_buffer else None
            )  # Clear any remaining characters in buffer

            self.logger.trace(f"read from {con_name}: '{res.decode()}'")
            # log the cleaned buffer if it's not empty
            if cleaned_buf:
                self.logger.trace(f"cleaned buffer: '{cleaned_buf.decode()}'")

        self.logger.debug(f"writing to {con_name}: '{cmd}'")
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
        """Check health of qemu. This is mostly just seeing if there's error
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

    def start(self, add_fwd_rules=True):
        """Start the virtual router"""
        self.logger.debug("Starting vrnetlab %s" % self.__class__.__name__)
        self.logger.debug("VMs: %s" % self.vms)
        if add_fwd_rules:
            run_command(
                ["socat", "TCP-LISTEN:22,fork", "TCP:127.0.0.1:2022"], background=True
            )
            run_command(
                ["socat", "UDP-LISTEN:161,fork", "UDP:127.0.0.1:2161"], background=True
            )
            run_command(
                ["socat", "TCP-LISTEN:830,fork", "TCP:127.0.0.1:2830"], background=True
            )
            run_command(
                ["socat", "TCP-LISTEN:80,fork", "TCP:127.0.0.1:2080"], background=True
            )
            run_command(
                ["socat", "TCP-LISTEN:443,fork", "TCP:127.0.0.1:2443"], background=True
            )

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
    """Our Qemu instance is somehow broken"""


# getMem returns the RAM size (in Mb) for a given VM mode.
# RAM can be specified in the variant dict, provided by a user via the custom type definition,
# or set via env vars.
# If set via env vars, the getMem will return this value as the most specific one.
# Otherwise, the ram provided to this function will be converted to Mb and returned.
def getMem(vmMode: str, ram: int) -> int:
    if vmMode == "integrated":
        # Integrated VM can use both MEMORY and CP_MEMORY env vars
        if "MEMORY" in os.environ:
            return 1024 * get_digits(os.getenv("MEMORY"))
        if "CP_MEMORY" in os.environ:
            return 1024 * get_digits(os.getenv("CP_MEMORY"))
    if vmMode == "cp":
        if "CP_MEMORY" in os.environ:
            return 1024 * get_digits(os.getenv("CP_MEMORY"))
    if vmMode == "lc":
        if "LC_MEMORY" in os.environ:
            return 1024 * get_digits(os.getenv("LC_MEMORY"))
    return 1024 * int(ram)


# getCpu returns the number of cpu cores for a given VM mode.
# Cpu can be specified in the variant dict, provided by a user via the custom type definition,
# or set via env vars.
# If set via env vars, the function will return this value as the most specific one.
# Otherwise, the number provided to this function via cpu param returned.
def getCpu(vsimMode: str, cpu: int) -> int:
    if vsimMode == "integrated":
        # Integrated VM can use both MEMORY and CP_MEMORY env vars
        if "CPU" in os.environ:
            return int(os.getenv("CPU"))
        if "CP_CPU" in os.environ:
            return int(os.getenv("CP_CPU"))
    if vsimMode == "cp":
        if "CP_CPU" in os.environ:
            return int(os.getenv("CP_CPU"))
    if vsimMode == "lc":
        if "LC_CPU" in os.environ:
            return int(os.getenv("LC_CPU"))
    return cpu


# strip all non-numeric characters from a string
def get_digits(input_str: str) -> int:
    non_string_chars = re.findall(r"\d", input_str)
    return int("".join(non_string_chars))
