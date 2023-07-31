#!/usr/bin/env python3

import datetime
import logging
import os
import re
import signal
import sys
import ftplib

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


# to allow writing config from ftp location we need to spin up a normal ftp client
# in the container host system. To access the host from qemu VM
# we needed to put the management interface in the container host network namespace
# this is done by putting the management interface with into a br-mgmt bridge
# the bridge and the mgmt interfaces will be addressed as follows
BRIDGE_ADDR = "172.31.255.29"
ROS_MGMT_ADDR = "172.31.255.30"
PREFIX_LENGTH = "30"
CONFIG_FILE = "/ftpboot/config.auto.rsc"


def trace(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kws)


logging.Logger.trace = trace


class ROS_vm(vrnetlab.VM):
    def __init__(self, hostname, username, password, conn_mode):
        for e in os.listdir("/"):
            if re.search(".vmdk$", e):
                disk_image = "/" + e
        super(ROS_vm, self).__init__(username, password, disk_image=disk_image, ram=256)
        self.qemu_args.extend(["-boot", "n"])
        self.hostname = hostname
        self.conn_mode = conn_mode
        self.num_nics = 31

        # set up bridge for management interface to a localhost
        self.logger.info("Creating br-mgmt bridge for management interface")
        # This is to whitlist all bridges
        vrnetlab.run_command(["mkdir", "-p", "/etc/qemu"])
        vrnetlab.run_command(["echo 'allow all' > /etc/qemu/bridge.conf"], shell=True)
        vrnetlab.run_command(["brctl", "addbr", "br-mgmt"])
        vrnetlab.run_command(
            ["echo 16384 > /sys/class/net/br-mgmt/bridge/group_fwd_mask"],
            shell=True,
        )
        vrnetlab.run_command(["ip", "link", "set", "br-mgmt", "up"])
        vrnetlab.run_command(
            ["ip", "addr", "add", "dev", "br-mgmt", f"{BRIDGE_ADDR}/{PREFIX_LENGTH}"]
        )

    def gen_mgmt(self):
        """
        Generate RouterOS MGMT interface connected to a mgmt bridge
        """

        res = []

        res.append("-device")

        res.append(
            self.nic_type + ",netdev=br-mgmt,mac=%(mac)s" % {"mac": vrnetlab.gen_mac(0)}
        )
        res.append("-netdev")
        res.append("bridge,br=br-mgmt,id=br-mgmt" % {"i": 0})

        return res

    def bootstrap_spin(self):
        """This function should be called periodically to do work."""

        if self.spins > 300:
            # too many spins with no result ->  give up
            self.stop()
            self.start()
            return

        (ridx, match, res) = self.tn.expect([b"MikroTik Login", b"RouterOS Login"], 1)
        if match:  # got a match!
            if ridx in (0, 1):  # login
                self.logger.debug("VM started")

                # Login
                self.wait_write("\r", None)
                # Append +ct to username for the plain-text console version

                # Mikrotik decided to change the prompt in the 6.48 line of code it seems
                if ridx == 0:
                    self.wait_write("admin+ct", wait="MikroTik Login: ")
                elif ridx == 1:
                    self.wait_write("admin+ct", wait="RouterOS Login: ")
                self.wait_write("", wait="Password: ")
                self.wait_write(
                    "n", wait="Do you want to see the software license? [Y/n]: "
                )

                # ROSv7 requires changing the password right away. ROSv6 does not require changing the password

                (ridx2, match2, _) = self.tn.expect([b"new password>"], 1)
                if match2 and ridx2 == 0:  # got a match! login
                    self.logger.debug("ROSv7 detected, setting admin password")
                    self.wait_write(f"{self.password}", wait="new password>")
                    self.wait_write(f"{self.password}", wait="repeat new password>")

                self.logger.debug("Login completed")

                # run main config!
                self.bootstrap_config()
                # close telnet connection
                self.tn.close()

                # If a config file exists, push it to the device
                if os.path.exists(CONFIG_FILE):
                    self.push_ftp_config()

                # startup time?
                startup_time = datetime.datetime.now() - self.start_time
                self.logger.info("Startup complete in: %s" % startup_time)
                # mark as running
                self.running = True
                return

        # no match, if we saw some output from the router it's probably
        # booting, so let's give it some more time
        if res != b"":
            self.logger.trace("OUTPUT: %s" % res.decode())
            # reset spins if we saw some output
            self.spins = 0

        self.spins += 1

        return

    def bootstrap_config(self):
        """Do the actual bootstrap config"""
        self.logger.info("applying bootstrap configuration")
        self.wait_write(f"/system identity set name={self.hostname}", wait="")

        self.wait_write(
            f"/ip address add interface=ether1 address={ROS_MGMT_ADDR}/{PREFIX_LENGTH}",
            f"[admin@{self.hostname}] > ",
        )
        # Update admin account if username==admin and there is a password set
        if self.username == "admin":
            if self.password != "":
                self.wait_write(
                    f"/user set {self.username} password={self.password}",
                    f"[admin@{self.hostname}] > ",
                )
        else:
            # Create new user if username != admin
            self.wait_write(
                f"/user add name={self.username} password={self.password} group=full",
                f"[admin@{self.hostname}] > ",
            )

        self.wait_write("\r", f"[admin@{self.hostname}] > ")
        self.logger.info("completed bootstrap configuration")

    def push_ftp_config(self):
        """Push the config file via"""
        self.logger.info("Pushing config via FTP")
        # Adding a retry field as FTP sometimes fails with a lot of nodes
        max_attempts = 5
        for i in range(1, max_attempts + 1):
            try:
                with ftplib.FTP(ROS_MGMT_ADDR, self.username, self.password) as session:
                    with open(CONFIG_FILE, "rb") as file:  # file to send
                        session.storbinary(
                            "STOR config.auto.rsc", file
                        )  # send the file
                        file.close()  # close file and FTP
                        session.quit()
                        break
            except ftplib.all_errors as e:
                self.logger.info(f"FTP attempt #{i} failed due to {str(e)}")
                if i != max_attempts:
                    self.logger.info("Trying again")
                else:
                    self.logger.info(f"Giving up after {max_attempts}")

        self.logger.info("config pushed via FTP")


class ROS(vrnetlab.VR):
    def __init__(self, hostname, username, password, conn_mode):
        super(ROS, self).__init__(username, password)
        self.vms = [ROS_vm(hostname, username, password, conn_mode)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--hostname", default="vr-ros", help="Router hostname")
    parser.add_argument(
        "--trace", action="store_true", help="enable trace level logging"
    )
    parser.add_argument("--username", default="vrnetlab", help="Username")
    parser.add_argument("--password", default="VR-netlab9", help="Password")
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

    # make ftpboot writable for saving ROS config
    vrnetlab.run_command(["chmod", "-R", "777", "/ftpboot"])

    # kill origin socats since we use bridge interface
    # for Router OS management interface
    # thus we need to forward connections to a different address
    vrnetlab.run_command(["pkill", "socat"])

    # redirecting incoming tcp traffic (except serial port 5000) from eth0 to RouterOS management interface
    vrnetlab.run_command(
        f"iptables-nft -t nat -A PREROUTING -i eth0 -p tcp ! --dport 5000 -j DNAT --to-destination {ROS_MGMT_ADDR}".split()
    )
    # same redirection but for UDP
    vrnetlab.run_command(
        f"iptables-nft -t nat -A PREROUTING -i eth0 -p udp -j DNAT --to-destination {ROS_MGMT_ADDR}".split()
    )
    # masquerading the incoming traffic so RouterOS is able to reply back
    vrnetlab.run_command(
        "iptables-nft -t nat -A POSTROUTING -o br-mgmt -j MASQUERADE".split()
    )

    # allow RouterOS breakout to management network by NATing via eth0
    vrnetlab.run_command("iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE".split())

    logger.debug(
        f"acting flags: username '{args.username}', password '{args.password}', connection-mode '{args.connection_mode}'"
    )

    logger.debug(f"Environment variables: {os.environ}")

    vrnetlab.boot_delay()

    vr = ROS(
        args.hostname,
        args.username,
        args.password,
        conn_mode=args.connection_mode,
    )
    vr.start(add_fwd_rules=False)
