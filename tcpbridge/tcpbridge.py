#!/usr/bin/env python3

import select
import socket
import sys


class TcpBridge:
    def __init__(self):
        self.sockets = []
        self.socket2remote = {}
        self.socket2hostintf = {}


    def routerintf2addr(self, hostintf):
        hostname, interface = hostintf.split("/")

        try:
            res = socket.getaddrinfo(hostname, "100%02d" % int(interface))
        except socket.gaierror:
            raise NoVR("Unable to resolve %s" % hostname)
        sockaddr = res[0][4]
        return sockaddr


    def add_p2p(self, p2p):
        source, destination = p2p.split("--")
        src_router, src_interface = source.split("/")
        dst_router, dst_interface = destination.split("/")

        src = self.routerintf2addr(source)
        dst = self.routerintf2addr(destination)

        left = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        right = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        left.connect(src)
        right.connect(dst)

        # add to list of sockets
        self.sockets.append(left)
        self.sockets.append(right)

        # dict for looking up remote in pair
        self.socket2remote[left] = right
        self.socket2remote[right] = left

        # dict to map back to hostname & interface
        self.socket2hostintf[left] = "%s/%s" % (src_router, src_interface)
        self.socket2hostintf[right] = "%s/%s" % (dst_router, dst_interface)
        

    def work(self):
        while True:
            try:
                ir,_,_ = select.select(self.sockets, [], [])
            except select.error as exc:
                break

            for i in ir:
                remote = self.socket2remote[i]
                try:
                    buf = i.recv(2048)
                except ConnectionResetError:
                    i.connect()
                if len(buf) == 0:
                    return
                if self.debug:
                    print("%05d bytes %s -> %s " % (len(buf), self.socket2hostintf[i], self.socket2hostintf[remote]))
                remote.send(buf)

class NoVR(Exception):
    """ No virtual router
    """
            

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action="store_true", default=False, help='enable debug')
    parser.add_argument('--p2p', nargs='+', help='point-to-point link')
    args = parser.parse_args()

    tt = TcpBridge()
    tt.debug = args.debug
    for p2p in args.p2p:
        try:
            tt.add_p2p(p2p)
        except NoVR as exc:
            print(exc, " Is it started and did you link it?")
            sys.exit(1)
    tt.work()
