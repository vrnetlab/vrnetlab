#!/usr/bin/env python3

from flask import Flask, json, request
import sys

# keep track of what we announce so we can easily withdraw
announced_routes = {}
# keep track of received routes
received_routes = {}

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
    to_announce = set(new_routes) - set(announced_routes)
    for prefix in to_announce:
        route = new_routes[prefix]

        command = "announce route %(prefix)s next-hop self" % route
        sys.stdout.write('%s\n' % command)
        sys.stdout.flush()

    # withdraw old routes
    to_withdraw = set(announced_routes) - set(new_routes)
    for prefix in to_withdraw:
        command = "withdraw route %s" % prefix
        sys.stdout.write('%s\n' % command)
        sys.stdout.flush()

    announced_routes = new_routes

    return 'announced: %d  withdrawn: %d  currently announcing: %d\n' % (len(to_announce), len(to_withdraw), len(announced_routes))


@app.route('/received', methods=['GET'])
def received():
    import sqlite3
    conn = sqlite3.connect('/tmp/bgp.db')
    c = conn.cursor()
    c.execute("SELECT prefix, attributes FROM received_routes")
    res = {}
    for row in c.fetchall():
        res[row[0]] = json.loads(row[1])

    return json.dumps(res)


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
