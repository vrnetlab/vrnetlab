#!/usr/bin/env python3

import select
import socket
import sys


class TcpBridge:
    def __init__(self):
        self.sockets = []
        self.socket2remote = {}


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

        self.add_bridge(src, dst)


    def add_bridge(self, left_addr, right_addr):
        left = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        right = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        left.connect(left_addr)
        right.connect(right_addr)

        # add to list of sockets
        self.sockets.append(left)
        self.sockets.append(right)

        # dict for looking up remote in pair
        self.socket2remote[left] = right
        self.socket2remote[right] = left
        

    def work(self):
        while True:
            try:
                ir,_,_ = select.select(self.sockets, [], [])
            except select.error as exc:
                break

            for i in ir:
                remote = self.socket2remote[i]
                buf = i.recv(2048)
                if len(buf) == 0:
                    return
                remote.send(buf)

class NoVR(Exception):
    """ No virtual router
    """
            

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--p2p', nargs='+', help='point-to-point link')
    args = parser.parse_args()

    tt = TcpBridge()
    for p2p in args.p2p:
        try:
            tt.add_p2p(p2p)
        except NoVR as exc:
            print(exc, " Is it started and did you link it?")
            sys.exit(1)
    tt.work()
