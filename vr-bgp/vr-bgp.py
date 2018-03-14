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


def calculate_ip_addressing(input_net, man_address, man_next_hop):
    """ Calculate IP addressing (address, neighbor, default route) on the specified interface

        This function is AFI agnostic, just feed it ipaddress objects.

        :param input_net: the IPv4/IPv6 network to use
        :param man_address: optional override for the host address
        :param man_next_hop: optional override for default route
        :return: tuple of (local_address, neighbor, next_hop, prefixlen)
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

    return str(address), str(neighbor), str(next_hop), net.prefixlen


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
    parser.add_argument('--listen', action="store_true", default=False, help='listen to incoming TCP connections')
    parser.add_argument('--local-as', required=True, help='local AS')
    parser.add_argument('--router-id', required=True, help='our router-id')
    parser.add_argument('--peer-as', required=True, help='peer AS')
    parser.add_argument('--md5', help='MD5')
    parser.add_argument('--trace', action='store_true', help='enable trace level logging')
    parser.add_argument('--vlan', type=int, help='VLAN ID to use')
    parser.add_argument('--ttl-security', action="store_true", help='Enable TTL security')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    config = {
        'IPV4_NEIGHBOR': None,
        'IPV6_NEIGHBOR': None,
        'IPV4_LOCAL_ADDRESS': None,
        'IPV6_LOCAL_ADDRESS': None,
        'LISTEN': args.listen,
        'LOCAL_AS': args.local_as,
        'PEER_AS': args.peer_as,
        'ROUTER_ID': args.router_id or '192.0.2.255',
        'MD5': args.md5,
        'INTERFACE': 'tap0',
        'INTERFACE_VLAN': None,
        'ALLOW_MIXED_AFI_TRANSPORT': args.allow_mixed_afi_transport,
        'TTLSECURITY': args.ttl_security
    }

    if args.vlan:
        vlan_intf = "tap0.{}".format(args.vlan)
        config['INTERFACE'] = vlan_intf
        config['INTERFACE_PHY'] = 'tap0'
        config['INTERFACE_VLAN'] = args.vlan



    if args.ipv4_prefix:
        config['IPV4_LOCAL_ADDRESS'], config['IPV4_NEIGHBOR'], config['IPV4_NEXT_HOP'], config['IPV4_PREFIXLEN'] = \
            calculate_ip_addressing(args.ipv4_prefix,
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
        config['IPV6_LOCAL_ADDRESS'], config['IPV6_NEIGHBOR'], config['IPV6_NEXT_HOP'], config['IPV6_PREFIXLEN'] = \
            calculate_ip_addressing(args.ipv6_prefix,
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

    # start vr-xcon & configure ip addressing
    if not os.path.exists("/dev/net/tun"):
        print("No TUN device - make sure you run the container with --privileged", file=sys.stderr)
        sys.exit(1)

    # start tcp2tap to listen on incoming TCP. vr-xcon will then connect us to
    # the virtual router
    xcon_params = ["/xcon.py", "--tap-listen", "1"]
    # if there is an address configured for v4/v6, pass it to xcon
    for af in (4, 6):
        if config["IPV{}_LOCAL_ADDRESS".format(af)]:
            address = "{}/{}".format(config["IPV{}_LOCAL_ADDRESS".format(af)], config["IPV{}_PREFIXLEN".format(af)])
            xcon_params.extend(("--ipv{}-address".format(af), address))
            xcon_params.extend(("--ipv{}-route".format(af), config["IPV{}_NEXT_HOP".format(af)]))
    if args.vlan:
        xcon_params.extend(("--vlan", str(args.vlan)))
    t2t = subprocess.Popen(xcon_params)

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
