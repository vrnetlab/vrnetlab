#!/usr/bin/env python3

import logging
import os
import signal
import subprocess
import sys
import time

import jinja2

def handle_SIGCHLD(signal, frame):
    os.waitpid(-1, os.WNOHANG)

def handle_SIGTERM(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, handle_SIGTERM)
signal.signal(signal.SIGTERM, handle_SIGTERM)
signal.signal(signal.SIGCHLD, handle_SIGCHLD)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action="store_true", help='enable debug')
    parser.add_argument('--ipv4-local-address', help='local address or route table will be used')
    parser.add_argument('--ipv4-neighbor', help='IP address of the neighbor')
    parser.add_argument('--ipv4-prefix', help='IP prefix to configure on the link')
    parser.add_argument('--ipv6-local-address', help='local address or route table will be used')
    parser.add_argument('--ipv6-neighbor', help='IP address of the neighbor')
    parser.add_argument('--ipv6-prefix', help='IP prefix to configure on the link')
    parser.add_argument('--local-as', required=True, help='local AS')
    parser.add_argument('--router-id', required=True, help='our router-id')
    parser.add_argument('--peer-as', required=True, help='peer AS')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # start tcp2tap to connect to virtual route
    t2t = subprocess.Popen(["/xcon.py", "--tap-listen", "1"])
    # wait for tcp2tap to bring up the tap0 interface
    time.sleep(1)
    subprocess.check_call(["ip", "link", "set", "tap0", "up"])
    if args.ipv4_prefix:
        subprocess.check_call(["ip", "address", "add", args.ipv4_prefix, "dev", "tap0"])
    if args.ipv6_prefix:
        subprocess.check_call(["ip", "address", "add", args.ipv6_prefix, "dev", "tap0"])

    config = {
        'IPV4_NEIGHBOR': args.ipv4_neighbor,
        'IPV6_NEIGHBOR': args.ipv6_neighbor,
        'IPV4_LOCAL_ADDRESS': None,
        'IPV6_LOCAL_ADDRESS': None,
        'LOCAL_AS': args.local_as,
        'PEER_AS': args.peer_as,
        'ROUTER_ID': args.router_id or '192.0.2.255',
    }
    if args.ipv4_local_address or args.ipv4_prefix:
        config['IPV4_LOCAL_ADDRESS'] = args.ipv4_local_address or args.ipv4_prefix.split("/")[0]
    if args.ipv6_local_address or args.ipv6_prefix:
        config['IPV6_LOCAL_ADDRESS'] = args.ipv6_local_address or args.ipv6_prefix.split("/")[0]
    if args.ipv4_neighbor and config['IPV4_LOCAL_ADDRESS'] is None:
        print("Please set --ipv4-prefix when --ipv4-neighbor is defined", file=sys.stderr)
        sys.exit(1)
    if args.ipv6_neighbor and config['IPV6_LOCAL_ADDRESS'] is None:
        print("Please set --ipv6-prefix when --ipv6-neighbor is defined", file=sys.stderr)
        sys.exit(1)


    # generate exabgp config - with Jinja2? get all the config options
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(['/']))
    template = env.get_template("/exabgp.conf.tpl")
    exa_config = open("/exabgp.conf", "w")
    exa_config.write(template.render(config=config))
    exa_config.close()
    # start exabgp
    exap = subprocess.Popen(["exabgp", "/exabgp.conf"])
    while True:
        time.sleep(1)

    # start BGPAPI!? EXPOSE
