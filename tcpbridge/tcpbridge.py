#!/usr/bin/env python3

import select
import socket


class TcpBridge:
    def __init__(self, config):
        self.sockets = []
        self.socket2remote = {}

        for pair in config:
            source = self.ep2addr(pair['source'])
            destination = self.ep2addr(pair['destination'])
            self.add_bridge(source, destination)
        print(self.sockets)


    def ep2addr(self, ep):
        """ Convert endpoint specification into TCP addr/port
        """
        port = "100%02d" % ep['interface']

        if 'address' in ep:
            return (ep['address'], port)

        elif 'router' in ep:
            print("Looking up", ep['router'])
            res = socket.getaddrinfo("vr%d" % ep['router'], port)
            print("res:", res)
            sockaddr = res[0][4]
            print("sockaddr:", sockaddr)
            return sockaddr


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
                print("Received from:", i)
                buf = i.recv(2048)
                if len(buf) == 0:
                    return
                print("Sending %d bytes to %s" % (len(buf), remote))
                remote.send(buf)
            

if __name__ == '__main__':
    config = [
        {
            'source': { 'router': 10, 'interface': 1 },
            'destination': { 'router': 11, 'interface': 1 }
        }
    ]

    tt = TcpBridge(config)
    tt.work()
