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


def config_ip(config, input_net, man_address, man_next_hop):
    """ Configure IP address on the tap0 interface and set default route

        This function is AFI agnostic, just feed it ipaddress objects
    """
    net = ipaddress.ip_network(input_net)
    if net.prefixlen == (net.max_prefixlen-1):
        address = net[0]
        neighbor = net[1]
        next_hop = net[1]
    else:
        address = net[1]
        neighbor = net[2]
        next_hop = net[2]

    # override default options
    if man_address:
        if ipaddress.ip_address(man_address) not in net:
            print("local address {} not in network {}".format(man_address, net), file=sys.stderr)
            sys.exit(1)
        address = ipaddress.ip_address(man_address)

    if man_next_hop:
        if ipaddress.ip_address(man_next_hop) not in net:
            print("next-hop address {} not in network {}".format(man_next_hop, net), file=sys.stderr)
            sys.exit(1)
        next_hop = ipaddress.ip_address(man_next_hop)

    # sanity checks
    if next_hop == address:
        print("default route next-hop address ({}) can not be the same as the local address ({})".format(next_hop, address), file=sys.stderr)
        sys.exit(1)

    print("network: {}  using address: {}".format(net, address))

    config['IPV{}_LOCAL_ADDRESS'.format(net.version)] = address
    config['IPV{}_NEIGHBOR'.format(net.version)] = neighbor

    subprocess.check_call(["ip", "-{}".format(net.version), "address", "add", str(address) + "/" + str(net.prefixlen), "dev", "tap0"])
    subprocess.check_call(["ip", "-{}".format(net.version), "route", "del", "default"])
    subprocess.check_call(["ip", "-{}".format(net.version), "route", "add", "default", "dev", "tap0", "via", str(next_hop)])



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action="store_true", help='enable debug')
    parser.add_argument('--ipv4-local-address', help='local address or route table will be used')
    parser.add_argument('--ipv4-neighbor', help='IP address of the neighbor')
    parser.add_argument('--ipv4-prefix', help='IP prefix to configure on the link')
    parser.add_argument('--ipv4-next-hop', help='next-hop address for IPv4 default route')
    parser.add_argument('--ipv6-local-address', help='local address or route table will be used')
    parser.add_argument('--ipv6-neighbor', help='IP address of the neighbor')
    parser.add_argument('--ipv6-prefix', help='IP prefix to configure on the link')
    parser.add_argument('--ipv6-next-hop', help='next-hop address for IPv6 default route')
    parser.add_argument('--allow-mixed-afi-transport', action='store_true', help='do not limit announced prefixes to neighbor AFI')
    parser.add_argument('--local-as', required=True, help='local AS')
    parser.add_argument('--router-id', required=True, help='our router-id')
    parser.add_argument('--peer-as', required=True, help='peer AS')
    parser.add_argument('--md5', help='MD5')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
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
        'MD5': args.md5,
        'ALLOW_MIXED_AFI_TRANSPORT': args.allow_mixed_afi_transport
    }

    subprocess.check_call(["ip", "link", "set", "tap0", "up"])
    if args.ipv4_prefix:
        config_ip(config, args.ipv4_prefix,
            args.ipv4_local_address,
            args.ipv4_next_hop)

        if args.ipv4_neighbor:
            config['IPV4_NEIGHBOR'] = args.ipv4_neighbor

    else:
        if args.ipv4_neighbor:
            print("--ipv4-neighbor requires --ipv4-prefix to be specified", file=sys.stderr)
            sys.exit(1)

        if args.ipv4_next_hop:
            print("--ipv4-next-hop requires --ipv4-prefix to be specified", file=sys.stderr)
            sys.exit(1)

        if args.ipv4_local_address:
            print("--ipv4-local-address requires --ipv4-prefix to be specified", file=sys.stderr)
            sys.exit(1)


    if args.ipv6_prefix:
        config_ip(config, args.ipv6_prefix,
            args.ipv6_local_address,
            args.ipv6_next_hop)

        if args.ipv6_neighbor:
            config['IPV6_NEIGHBOR'] = args.ipv6_neighbor

    else:
        if args.ipv6_neighbor:
            print("--ipv6-neighbor requires --ipv6-prefix to be specified", file=sys.stderr)
            sys.exit(1)

        if args.ipv6_next_hop:
            print("--ipv6-next-hop requires --ipv6-prefix to be specified", file=sys.stderr)
            sys.exit(1)

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
        if exap.poll() == 0:
            print("exabgp stopped, restarting in 2s")
            time.sleep(2)
            exap = subprocess.Popen(["exabgp", "/exabgp.conf"])
        time.sleep(1)
