#!/usr/bin/env python3

import logging
import subprocess
import sys
import time

import jinja2


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action="store_true", help='enable debug')
    parser.add_argument('--ip-prefix', required=True, help='IP prefix to configure on the link')
    parser.add_argument('--local-as', required=True, help='local AS')
    parser.add_argument('--local-address', help='local address or route table will be used')
    parser.add_argument('--neighbor', required=True, help='IP address of the neighbor')
    parser.add_argument('--router-id', required=True, help='our router-id')
    parser.add_argument('--peer-as', required=True, help='peer AS')
    parser.add_argument('--vr', required=True, help='virtual router and interface to connect to, e.g. vr-1/1')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # start tcp2tap to connect to virtual route
    t2t = subprocess.Popen(["/xcon.py", "--vr2tap", args.vr])
    # wait for tcp2tap to bring up the tap0 interface
    time.sleep(1)
    subprocess.check_call(["ip", "link", "set", "tap0", "up"])
    subprocess.check_call(["ip", "address", "add", args.ip_prefix, "dev", "tap0"])

    config = {
        'NEIGHBOR': args.neighbor,
        'LOCAL_ADDRESS': args.local_address or args.ip_prefix.split("/")[0],
        'LOCAL_AS': args.local_as,
        'PEER_AS': args.peer_as,
        'ROUTER_ID': args.router_id or '192.0.2.255',
    }

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
