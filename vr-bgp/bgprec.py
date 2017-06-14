#!/usr/bin/env python3

from datetime import datetime
import json
import sqlite3
import sys

# debug log file
f = open("/tmp/bgp.log", "a")

def log(msg):
    f.write(msg)
    f.write("\n")
    f.flush()

conn = sqlite3.connect('/tmp/bgp.db', detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()
try:
    c.execute("SELECT * FROM received_routes")
except sqlite3.OperationalError:
    # create table to store received routes
    c.execute("CREATE TABLE received_routes (afi string, prefix string, attributes string)")
    c.execute("CREATE UNIQUE INDEX received_routes__prefix ON received_routes(afi, prefix)")

    # create table to store neighbor state
    c.execute("CREATE TABLE neighbors (ip string, state string, ts timestamp)")
    c.execute("CREATE UNIQUE INDEX neighbors_ip ON neighbors(ip)")


def upsert_neighbor_state(ip, state, timestamp):
    """ Insert or update the state of a neighbor in the database
    """
    c.execute("SELECT * FROM neighbors WHERE ip=?", [ip])
    if c.fetchone() is None:
        log("INSERTING to db neighbor")
        c.execute("INSERT INTO neighbors (ip, state, ts) VALUES (?, ?, ?)", [ip, state, timestamp])
    else:
        log("UPDATING db neighbor\n")
        c.execute("UPDATE neighbors SET state = ?, ts = ? WHERE ip = ?", [state, timestamp, ip])
    conn.commit()


def upsert_prefix(afi, prefix, attributes):
    """ Insert or update a prefix in the database
    """
    c.execute("SELECT * FROM received_routes WHERE afi=? AND prefix=?", [afi, prefix])
    if c.fetchone() is None:
        log("INSERTING to db prefix")
        c.execute("INSERT INTO received_routes (afi, prefix, attributes) VALUES (?, ?, ?)", [afi, prefix, json.dumps(attributes)])
    else:
        log("UPDATING db prefix")
        c.execute("UPDATE received_routes SET attributes = ? WHERE afi = ? AND prefix = ?", [json.dumps(attributes), afi, prefix])
    conn.commit()


def remove_prefix(afi, prefix):
    """ Remove a prefix from the database
    """
    c.execute("DELETE FROM received_routes WHERE afi=? AND prefix=?", [afi, prefix])
    conn.commit()


def parse_message(line):
    # Parse JSON string  to dictionary
    msg = json.loads(line)

    timestamp = datetime.fromtimestamp(msg['time'])

    if msg['type'] == 'state':
        neighbor_ip = msg['neighbor']['ip']
        state = msg['neighbor']['state']
        upsert_neighbor_state(neighbor_ip, state, timestamp)

    if msg['type'] == 'update':
        if 'update' in msg['neighbor']['message']:
            update = msg['neighbor']['message']['update']

            # handle announce
            if 'announce' in update:
                for afi, nexthops in update['announce'].items():
                    if 'null' in nexthops:
                        log("Received EOR for {}".format(afi))
                    else:
                        for nexthop, prefixes in nexthops.items():
                            if nexthop.startswith('fe80:'):
                                # ignore IPv6 link local next-hops. BGP sends
                                # both LL next-hop and GUA so we just ignore LL
                                # and parse GUA
                                continue
                            for prefix in prefixes:
                                log("announce {}".format(prefix))
                                attributes = update['attribute']
                                # store next-hop, which is NLRI information as
                                # (path) attribute. this is not according to
                                # RFC but gosh does it simplify things.
                                attributes['next-hop'] = nexthop
                                upsert_prefix(afi, prefix, attributes)

            # handle withdraws
            if 'withdraw' in update:
                for afi, prefixes in update['withdraw'].items():
                    for prefix in prefixes:
                        log("Withdraw {}".format(prefix))
                        remove_prefix(afi, prefix)
        elif 'eor' in msg['neighbor']['message']:
            eor = msg['neighbor']['message']['eor']
            log("Received EOR for {} {}".format(eor['afi'], eor['safi']))
        else:
            log("Unknown message")
            raise Exception("Unknown message")


blank = 0
while True:
    line = sys.stdin.readline().strip()

    # abort if we just see blank lines - prolly means exa died
    if line == "":
        blank += 1
        # got 99 blank lines and this is one
        if blank > 99:
            break
        continue
    blank = 0

    f.write(line + "\n")
    f.flush()
    parse_message(line)
