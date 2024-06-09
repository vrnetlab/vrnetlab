#!/usr/bin/env python3
import datetime
import logging
import os
import re
import signal
import sys
import uuid

import vrnetlab


def handle_SIGCHLD(_unused_signal, _unused_frame):
    os.waitpid(-1, os.WNOHANG)


def handle_SIGTERM(_unused_signal, _unused_frame):
    sys.exit(0)


signal.signal(signal.SIGINT, handle_SIGTERM)
signal.signal(signal.SIGTERM, handle_SIGTERM)
signal.signal(signal.SIGCHLD, handle_SIGCHLD)

TRACE_LEVEL_NUM = 9
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


def trace(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self.log(TRACE_LEVEL_NUM, message, *args, **kws)


logging.Logger.trace = trace


class FortiOS_vm(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode):
        for e in os.listdir("."):
            if re.search(".qcow2$", e):
                disk_image = "./" + e
        # call parents __init__ function here
        super(FortiOS_vm, self).__init__(
            username,
            password,
            disk_image=disk_image,
            ram=2048,
            driveif="virtio",
            # fortios fails to respond to network requests if the pci bus is setup :D
            provision_pci_bus=False,
        )
        self.conn_mode = conn_mode
        self.hostname = hostname
        self.num_nics = 12
        self.nic_type = "virtio-net-pci"
        self.highest_port = 0
        self.qemu_args.extend(["-uuid", str(uuid.uuid4())])
        self.spins = 0
        self.running = None

        # set up the extra empty disk image
        # for fortigate logs
        vrnetlab.run_command(
            ["qemu-img", "create", "-f", "qcow2", "empty.qcow2", "30G"]
        )

        self.qemu_args.extend(
            [
                "-drive",
                "if=virtio,format=qcow2,file=empty.qcow2,index=1",
            ]
        )


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

        (ridx, match, res) = self.tn.expect([b"login:", b"FortiGate-VM64-KVM #"], 1)
        if match:  # got a match!
            if ridx == 0:  # matched login prompt, so should login
                self.logger.debug("ridx == 0")
                self.logger.info("matched login prompt")

                self.wait_write(self.username, wait=None)
                self.wait_write("", wait=self.username)
                self.wait_write(self.password, wait="Password")
                self.wait_write(self.password, wait=None)

            if ridx == 1:
                # if we dont match the FortiGate-VM64-KVM # we assume we already have some configuration and
                # may continue with configure the system to our needs.
                self.logger.debug("ridx == 1")
                self.wait_write("config system global", wait=None)
                hostname_command = "set hostname " + self.hostname
                self.wait_write(hostname_command, wait="global")
                self.wait_write("end", wait=hostname_command)
                self.running = True
                self.tn.close()
                # calc startup time
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info(f"Startup complete in { startup_time }")
                return

        else:
            # no match, if we saw some output from the router it's probably
            # booting, so let's give it some more time
            if res != b"":
                self.logger.trace(f"OUTPUT FORTIGATE: {res.decode()}")
                # reset spins if we saw some output
                self.spins = 0

        self.spins += 1

    def _wait_reset(self):
        """
        This function waits for the login prompt after the VM was resetted.
        If commands are issued that enforce a reboot this comes in hand.
        e.g factoryreset or factoryreset2
        """
        self.logger.debug("waiting for reset")
        wait_spins = 0
        while wait_spins < 90:
            _, match, data = self.tn.expect([b"login: "], timeout=10)
            self.logger.trace(data.decode("UTF-8"))
            if match:
                self.logger.debug("reset finished")
                return True
            wait_spins += 1
        self.logger.error("Reset took to long")
        return False


class FortiOS(vrnetlab.VR):
    def __init__(self, hostname, username, password, conn_mode):
        super(FortiOS, self).__init__(username, password)
        self.logger.debug("Hostname")
        self.logger.debug(hostname)
        self.vms = [FortiOS_vm(hostname, username, password, conn_mode)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--hostname", default="vr-fortinet", help="Fortinet hostname")
    parser.add_argument("--username", default="admin", help="Username")
    parser.add_argument("--password", default="admin", help="Password")
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
    vr = FortiOS(
        args.hostname, args.username, args.password, conn_mode=args.connection_mode
    )
    vr.start()
