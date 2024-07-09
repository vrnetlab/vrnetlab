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
        logging.getLogger().info(f"Delaying VM boot by {delay} seconds")
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

    def __init__(
        self,
        username,
        password,
        disk_image="",
        num=0,
        ram=4096,
        driveif="ide",
        provision_pci_bus=True,
        cpu="host",
        smp="1",
        min_dp_nics=0,
    ):
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

        self._ram = ram
        self._cpu = cpu
        self._smp = smp

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
        
        self.insuffucient_nics = False
        self.min_nics = 0
        # if an image needs minimum amount of dataplane nics to bootup, specify
        if min_dp_nics:
            self.min_nics = min_dp_nics

        # we setup pci bus by default
        self.provision_pci_bus = provision_pci_bus
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

        self.qemu_args = [
            "qemu-system-x86_64",
            "-display",
            "none",
            "-machine",
            "pc",
            "-monitor",
            f"tcp:0.0.0.0:40{self.num:02d},server,nowait",
            "-serial",
            f"telnet:0.0.0.0:50{self.num:02d},server,nowait",
            "-m",  # memory
            str(self.ram),
            "-cpu",  # cpu type
            self.cpu,
            "-smp",
            self.smp,  # cpu core configuration
            "-drive",
            f"if={driveif},file={overlay_disk_image}",
        ]

        # add additional qemu args if they were provided
        if self.qemu_additional_args:
            self.qemu_args.extend(self.qemu_additional_args)

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
        if self.provision_pci_bus:
            for i in range(1, math.ceil(self.num_nics / self.nics_per_pci_bus) + 1):
                cmd.extend(["-device", f"pci-bridge,chassis_nr={i},id=pci.{i}"])

        # generate mgmt NICs
        cmd.extend(self.gen_mgmt())
        # generate normal NICs
        cmd.extend(self.gen_nics())
        # generate dummy NICs
        if self.insuffucient_nics:
            cmd.extend(self.gen_dummy_nics())

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

    def gen_mgmt(self):
        """Generate qemu args for the mgmt interface(s)"""
        res = []
        # mgmt interface is special - we use qemu user mode network
        res.append("-device")
        mac = (
            "c0:00:01:00:ca:fe"
            if getattr(self, "_static_mgmt_mac", False)
            else gen_mac(0)
        )
        res.append(self.nic_type + f",netdev=p00,mac={mac}")
        res.append("-netdev")
        res.append(
            "user,id=p00,net=10.0.0.0/24,"
            "tftp=/tftpboot,"
            "hostfwd=tcp::2022-10.0.0.15:22,"  # ssh
            "hostfwd=udp::2161-10.0.0.15:161,"  # snmp
            "hostfwd=tcp::2830-10.0.0.15:830,"  # netconf
            "hostfwd=tcp::2080-10.0.0.15:80,"  # http
            "hostfwd=tcp::2443-10.0.0.15:443,"  # https
            "hostfwd=tcp::49339-10.0.0.15:9339,"  # iana gnmi/gnoi
            "hostfwd=tcp::47400-10.0.0.15:57400,"  # nokia gnmi/gnoi
            "hostfwd=tcp::56030-10.0.0.15:6030,"  # gnmi/gnoi arista
            "hostfwd=tcp::52767-10.0.0.15:32767"  # gnmi/gnoi juniper
        )
        return res

    def nic_provision_delay(self) -> None:
        self.logger.debug(
            f"number of provisioned data plane interfaces is {self.num_provisioned_nics}"
        )

        # no nics provisioned and/or not running from containerlab so we can bail
        if self.num_provisioned_nics == 0:
            # unless the node has a minimum nic requirement
            if self.min_nics:
                self.insuffucient_nics = True
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
                break
            time.sleep(5)
        
        # check if we need to provision any more nics, do this after because they shouldn't interfere with the provisioned nics
        if self.num_provisioned_nics < self.min_nics:
            self.insuffucient_nics = True

    # if insuffucient amount of nics are defined in the topology file, generate dummmy nics so cat9kv can boot.
    def gen_dummy_nics(self):
        # calculate required num of nics to generate
        nics = self.min_nics - self.num_provisioned_nics
        
        self.logger.debug(f"Insuffucient NICs defined. Generating {nics} dummy nics")

        res=[]
        
        pci_bus_ctr = self.num_provisioned_nics

        for i in range(0, nics):
            # dummy interface naming
            interface_name = f"dummy{str(i+self.num_provisioned_nics)}"
            
            # PCI bus counter is to ensure pci bus index starts from 1
            # and continuing in sequence regardles the eth index
            pci_bus_ctr += 1

            pci_bus = math.floor(pci_bus_ctr / self.nics_per_pci_bus) + 1
            addr = (pci_bus_ctr % self.nics_per_pci_bus) + 1
            
            res.extend(
                [
                    "-device",
                    f"{self.nic_type},netdev={interface_name},id={interface_name},mac={gen_mac(i)},bus=pci.{pci_bus},addr=0x{addr}",
                    "-netdev",
                    f"tap,ifname={interface_name},id={interface_name},script=no,downscript=no",
                ]
            )
        return res

    def gen_nics(self):
        """Generate qemu args for the normal traffic carrying interface(s)"""
        self.nic_provision_delay()

        res = []

        if self.conn_mode == "tc":
            self.create_tc_tap_ifup()

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
                        f"{self.nic_type},netdev=p{i:02d}"
                        + (
                            f",bus=pci.{pci_bus},addr=0x{addr:x}"
                            if self.provision_pci_bus
                            else ""
                        ),
                        "-netdev",
                        f"socket,id=p{i:02d},listen=:{i + 10000:02d}",
                    ]
                )
                continue

            mac = gen_mac(i)

            res.append("-device")
            res.append(
                f"{self.nic_type},netdev=p{i:02d},mac={mac}"
                + (
                    f",bus=pci.{pci_bus},addr=0x{addr:x}"
                    if self.provision_pci_bus
                    else ""
                ),
            )

            if self.conn_mode == "tc":
                res.append("-netdev")
                res.append(
                    f"tap,id=p{i:02d},ifname=tap{i},script=/etc/tc-tap-ifup,downscript=no"
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

    @property
    def version(self):
        """Read version number from VERSION environment variable

        The VERSION environment variable is set at build time using the value
        from the makefile. If the environment variable is not defined please add
        the variables in the Dockerfile (see csr)"""
        version = os.environ.get("VERSION")
        if version is not None:
            return version
        raise ValueError("The VERSION environment variable is not set")

    @property
    def ram(self):
        """
        Read memory size from the QEMU_MEMORY environment variable and use it in the qemu parameters for the VM.
        If the QEMU_MEMORY environment variable is not set, use the default value.
        Should be provided as a number of MB. e.g. 4096.
        """

        if "QEMU_MEMORY" in os.environ:
            return get_digits(str(os.getenv("QEMU_MEMORY")))

        return self._ram

    @property
    def cpu(self):
        """
        Read the CPU type the QEMU_CPU environment variable and use it in the qemu parameters for the VM.
        If the QEMU_CPU environment variable is not set, use the default value.
        """

        if "QEMU_CPU" in os.environ:
            return str(os.getenv("QEMU_CPU"))

        return str(self._cpu)

    @property
    def smp(self):
        """
        Read SMP parameter (e.g. number of CPU cores) from the QEMU_SMP environment variable.
        If the QEMU_SMP parameter is not set, the default value is used.
        Should be provided as a number, e.g. 2
        """

        if "QEMU_SMP" in os.environ:
            return str(os.getenv("QEMU_SMP"))

        return str(self._smp)

    @property
    def qemu_additional_args(self):
        """
        Read additional qemu arguments (e.g. number of CPU cores) from the QEMU_ADDITIONAL_ARGS environment variable.
        If the QEMU_ADDITIONAL_ARGS parameter is not set, nothing is added to the default args set.
        Should be provided as a space separated list of arguments, e.g. "-machine pc -display none"
        """

        if "QEMU_ADDITIONAL_ARGS" in os.environ:
            s = str(os.getenv("QEMU_ADDITIONAL_ARGS"))
            if s:
                return s.split()


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
            # IANA gnmi/gnoi
            run_command(
                ["socat", "TCP-LISTEN:9339,fork", "TCP:127.0.0.1:49339"],
                background=True,
            )
            # Nokia gnmi/gnoi
            run_command(
                ["socat", "TCP-LISTEN:57400,fork", "TCP:127.0.0.1:47400"],
                background=True,
            )
            # Arista gnmi/gnoi
            run_command(
                ["socat", "TCP-LISTEN:57400,fork", "TCP:127.0.0.1:47400"],
                background=True,
            )
            # Juniper gnmi/gnoi
            run_command(
                ["socat", "TCP-LISTEN:32767,fork", "TCP:127.0.0.1:52767"],
                background=True,
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


def get_digits(input_str: str) -> int:
    """
    Strip all non-numeric characters from a string
    """

    non_string_chars = re.findall(r"\d", input_str)
    return int("".join(non_string_chars))


class VR_Installer:
    def __init__(self):
        self.logger = logging.getLogger()
        self.vm = None

    def install(self):
        vm = self.vm
        while not vm.running:
            self.logger.trace("%s working", self.__class__.__name__)
            vm.work()
        self.logger.debug("%s running, shutting down", self.__class__.__name__)
        vm.stop()
        self.logger.info("Installation complete")
