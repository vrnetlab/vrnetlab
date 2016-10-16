#!/usr/bin/env python3

import ipaddress
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

    if not os.path.exists("/dev/net/tun"):
        print("No TUN device - make sure you run the container with --privileged", file=sys.stderr)
        sys.exit(1)

    # start tcp2tap to listen on incoming TCP. vr-xcon will then connect us to
    # the virtual router
    t2t = subprocess.Popen(["/xcon.py", "--tap-listen", "1"])
    # wait for tcp2tap to bring up the tap0 interface
    time.sleep(1)

    config = {
        'IPV4_NEIGHBOR': None,
        'IPV6_NEIGHBOR': None,
        'IPV4_LOCAL_ADDRESS': None,
        'IPV6_LOCAL_ADDRESS': None,
        'LOCAL_AS': args.local_as,
        'PEER_AS': args.peer_as,
        'ROUTER_ID': args.router_id or '192.0.2.255',
    }

    subprocess.check_call(["ip", "link", "set", "tap0", "up"])
    if args.ipv4_prefix:
        ipv4_net = ipaddress.IPv4Network(args.ipv4_prefix)
        if ipv4_net.prefixlen == 31:
            ipv4_address = ipv4_net[0]
            ipv4_neighbor = ipv4_net[1]
        else:
            ipv4_address = ipv4_net[1]
            ipv4_neighbor = ipv4_net[2]

        if args.ipv4_local_address:
            if ipaddress.IPv4Address(args.ipv4_local_address) not in ipv4_net:
                print("--ipv4-local-address {} is not in --ipv4-prefix {}".format(args.ipv4_local_address, args.ipv4_prefix), file=sys.stderr)
                sys.exit(1)
            ipv4_address = ipaddress.IPv4Address(args.ipv4_local_address)

        if args.ipv4_neighbor:
            if ipaddress.IPv4Address(args.ipv4_neighbor) not in ipv4_net:
                print("--ipv4-neighbor {} is not in --ipv4-prefix {}".format(args.ipv4_neighbor, args.ipv4_prefix), file=sys.stderr)
                sys.exit(1)
            ipv4_neighbor = ipaddress.IPv4Address(args.ipv4_neighbor)

        if args.ipv4_neighbor is not None and args.ipv4_local_address == args.ipv4_neighbor:
            print("--ipv4-neighbor {} cannot be the same as --ipv4-local-address".format(args.ipv4_neighbor, args.ipv4_local_address), file=sys.stderr)
            sys.exit(1)

        print("IPv4 network: {}  using IPv4 address: {} and IPv4 neighbor: {}".format(ipv4_net, ipv4_address, ipv4_neighbor))

        config['IPV4_LOCAL_ADDRESS'] = ipv4_address
        config['IPV4_NEIGHBOR'] = ipv4_neighbor

        subprocess.check_call(["ip", "address", "add", str(ipv4_address) + "/" + str(ipv4_net.prefixlen), "dev", "tap0"])
    else:
        if args.ipv4_local_address:
            print("--ipv4-local-address requires --ipv4-prefix to be specified", file=sys.stderr)
            sys.exit(1)


    if args.ipv6_prefix:
        ipv6_net = ipaddress.IPv6Network(args.ipv6_prefix)
        if ipv6_net.prefixlen == 127:
            ipv6_address = ipv6_net[0]
            ipv6_neighbor = ipv6_net[1]
        else:
            ipv6_address = ipv6_net[1]
            ipv6_neighbor = ipv6_net[2]

        if args.ipv6_local_address:
            if ipaddress.IPv6Address(args.ipv6_local_address) not in ipv6_net:
                print("--ipv6-local-address {} is not in --ipv6-prefix {}".format(args.ipv6_local_address, args.ipv6_prefix), file=sys.stderr)
                sys.exit(1)
            ipv6_address = ipaddress.IPv6Address(args.ipv6_local_address)

        if args.ipv6_neighbor:
            if ipaddress.IPv6Address(args.ipv6_neighbor) not in ipv6_net:
                print("--ipv6-neighbor {} is not in --ipv6-prefix {}".format(args.ipv6_neighbor, args.ipv6_prefix), file=sys.stderr)
                sys.exit(1)
            ipv6_neighbor = ipaddress.IPv6Address(args.ipv6_neighbor)

        if args.ipv6_neighbor is not None and args.ipv6_local_address == args.ipv6_neighbor:
            print("--ipv6-neighbor {} cannot be the same as --ipv6-local-address".format(args.ipv6_neighbor, args.ipv6_local_address), file=sys.stderr)
            sys.exit(1)

        print("IPv6 network: {}  using IPv6 address: {} and IPv6 neighbor: {}".format(ipv6_net, ipv6_address, ipv6_neighbor))

        config['IPV6_LOCAL_ADDRESS'] = ipv6_address
        config['IPV6_NEIGHBOR'] = ipv6_neighbor

        subprocess.check_call(["ip", "address", "add", str(ipv6_address) + "/" + str(ipv6_net.prefixlen), "dev", "tap0"])
    else:
        if args.ipv6_local_address:
            print("--ipv6-local-address requires --ipv6-prefix to be specified", file=sys.stderr)
            sys.exit(1)


    # generate exabgp config using Jinja2 template
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(['/']))
    template = env.get_template("/exabgp.conf.tpl")
    exa_config = open("/exabgp.conf", "w")
    exa_config.write(template.render(config=config))
    exa_config.close()
    # start exabgp
    exap = subprocess.Popen(["exabgp", "/exabgp.conf"])
    while True:
        time.sleep(1)
