#!/usr/bin/env python3

from datetime import datetime
import json
import sqlite3
import sys

# debug log file
f = open("/tmp/bgp.log", "a")

conn = sqlite3.connect('/tmp/bgp.db', detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()
try:
    c.execute("SELECT * FROM received_routes")
except sqlite3.OperationalError:
    # create table to store received routes
    c.execute("CREATE TABLE received_routes (prefix string, attributes string)")
    c.execute("CREATE UNIQUE INDEX received_routes__prefix ON received_routes(prefix)")

    # create table to store neighbor state
    c.execute("CREATE TABLE neighbors (ip string, state string, ts timestamp)")
    c.execute("CREATE UNIQUE INDEX neighbors_ip ON neighbors(ip)")


def upsert_neighbor_state(ip, state, timestamp):
    f.write("selecting %s from database\n" % ip)  
    f.flush()
    c.execute("SELECT * FROM neighbors WHERE ip=?", [ip])
    if c.fetchone() is None:
        f.write("INSERTING to db\n")
        f.flush()
        c.execute("INSERT INTO neighbors (ip, state, ts) VALUES (?, ?, ?)", [ip, state, timestamp])
    else:
        f.write("UPDATING db\n")
        f.flush()
        c.execute("UPDATE neighbors SET state = ?, ts = ? WHERE ip = ?", [state, timestamp, ip])
    conn.commit()


def upsert_prefix(prefix, attributes):
    f.write("selecting %s from database\n" % prefix)  
    f.flush()
    c.execute("SELECT * FROM received_routes WHERE prefix=?", [prefix])
    if c.fetchone() is None:
        f.write("INSERTING to db\n")
        f.flush()
        c.execute("INSERT INTO received_routes (prefix, attributes) VALUES (?, ?)", [prefix, json.dumps(attributes)])
    else:
        f.write("UPDATING db\n")
        f.flush()
        c.execute("UPDATE received_routes SET attributes = ? WHERE prefix = ?", [json.dumps(attributes), prefix])
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
        update = msg['neighbor']['message']['update']
        for afi, neighbors in update['announce'].items():
            for neighbor, prefixes in neighbors.items():
                for prefix in prefixes:
                    attributes = update['attribute']
                    upsert_prefix(prefix, attributes)

# TODO: handle withdraw:
# { "exabgp": "3.4.8", "time": 1471261200, "host" : "413d35cc0b6b", "pid" : "15", "ppid" : "1", "counter": 5, "type": "update", "neighbor": { "ip": "192.168.1.1", "address": { "local": "192.168.1.2", "peer": "192.168.1.1"}, "asn": { "local": "15169", "peer": "2792"}, "message": { "update": { "withdraw": { "ipv4 unicast": { "1.1.1.0/24": {  } } } } }} }

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
