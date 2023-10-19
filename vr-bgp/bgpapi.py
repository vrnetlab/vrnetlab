#!/usr/bin/env python3

from flask import Flask, json, request
from typing import Optional, Tuple
import re
import sys
import subprocess
import ipaddress

# keep track of what we announce so we can easily withdraw
announced_routes = {}
# keep track of received routes
received_routes = {}

def log(msg):
    with open("/tmp/bgpapi.log", "a") as f:
        if isinstance(msg, bytes):
            f.write(msg.decode("utf-8"))
        else:
            f.write(str(msg))
        f.write("\n")
        f.flush()


def _get_pingable_address(route, prefix) -> Optional[Tuple[str, int]]:
    if "pingable-auto" in route and route["pingable-auto"]:
        net = ipaddress.ip_network(prefix)
        # wrapping with iter() is usually not necessary, except for prefixlen=32
        # net.hosts() is actually a list (= not an iterator)
        return str(next(iter(net.hosts()))), net.prefixlen
    elif "pingable-address" in route:
        address, prefixlen = route["pingable-address"].split("/")
        return address, int(prefixlen)
    return None


def add_address(address, prefixlen):
    """ Add the host address to the loopback interface
    """
    try:
        cmd = f"sudo ip address add {address}/{prefixlen} dev lo"
        log(cmd)
        subprocess.check_output(cmd,  stderr=subprocess.STDOUT, shell=True)
        log(f"Configured {address}/{prefixlen} on lo")
    except subprocess.CalledProcessError as cpe:
        log(f"Failed to configure {address}/{prefixlen} on lo")
        log(cpe.output)

def remove_address(address, prefixlen):
    """ Remove the address from the loopback interface
    """
    try:
        cmd = f"sudo ip address del {address}/{prefixlen} dev lo"
        log(cmd)
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        log(f"Removed {address}/{prefixlen} from lo")
    except subprocess.CalledProcessError as cpe:
        log(f"Failed to remove {address}/{prefixlen} from lo")
        log(cpe.output)


def update_default_route(source_address=None):
    """ Update the source address on the default route
    """
    try:
        cmd = f"sudo ip route | grep default"
        route = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode("utf-8").splitlines()[0]
        route = re.sub(r"\s+src [a-f0-9:.]+$", "", route)
        if source_address:
            cmd = f"sudo ip route change {route} src {source_address}"
        else:
            cmd = f"sudo ip route change {route}"
        log(cmd)
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        log(f"Added src={source_address} on default route")
    except subprocess.CalledProcessError as cpe:
        log(f"Failed to set src={source_address} on default route")
        log(cpe.output)


app = Flask(__name__)

@app.route('/announce', methods=['POST'])
def announce():
    global announced_routes

    if request.headers['Content-Type'] != 'application/json':
        return "Plxz send JSON"

    try:
        routes = request.json['routes']
        new_routes = {route['prefix']: route for route in routes}
    except:
        return "Incorrectly formed query (probably)"

    # announce new routes
    to_announce = set(new_routes)
    for prefix in to_announce:
        route = new_routes[prefix]

        command = "announce route %(prefix)s next-hop self" % route
        if 'community' in route:
            command += " community [" + " ".join(route['community']) + "]"
        if 'med' in route:
            command += " med " + str(route['med'])
        if 'as-path' in route:
            command += " as-path [" + " ".join([str(x) for x in route['as-path']]) + "]"
        sys.stdout.write('%s\n' % command)
        sys.stdout.flush()

        if pingable_address := _get_pingable_address(route, prefix):
            add_address(*pingable_address)
            if route.get("pingable-address-as-source", False):
                update_default_route(pingable_address[0])
        else:
            update_default_route()

    # withdraw old routes
    to_withdraw = set(announced_routes) - set(new_routes)
    for prefix in to_withdraw:
        command = "withdraw route %s" % prefix
        sys.stdout.write('%s\n' % command)
        sys.stdout.flush()

        route = announced_routes[prefix]
        if pingable_address := _get_pingable_address(route, prefix):
            remove_address(*pingable_address)
            if route.get("pingable-address-as-source", False):
                update_default_route()

    announced_routes = new_routes

    return 'announced: %d  withdrawn: %d  currently announcing: %d\n' % (len(to_announce), len(to_withdraw), len(announced_routes))


@app.route('/received', methods=['GET'])
def received():
    import sqlite3
    conn = sqlite3.connect('/tmp/bgp.db')
    c = conn.cursor()
    c.execute("SELECT afi, prefix, attributes FROM received_routes")
    res = {}
    for row in c.fetchall():
        if row[0] not in res:
            res[row[0]] = {}
        res[row[0]][row[1]] = json.loads(row[2])

    return json.dumps(res)


@app.route('/neighbors', methods=['GET'])
def get_neighbors():
    import sqlite3
    conn = sqlite3.connect('/tmp/bgp.db')
    c = conn.cursor()
    c.execute("SELECT ip, state, ts FROM neighbors")
    res = {}
    for row in c.fetchall():
        res[row[0]] = {
            'state': row[1],
            'timestamp': row[2]
        }

    return json.dumps(res)


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
