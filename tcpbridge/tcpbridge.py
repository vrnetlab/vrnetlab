#!/usr/bin/env python3

import logging
import select
import socket
import sys


class TcpBridge:
    def __init__(self):
        self.logger = logging.getLogger()
        self.sockets = []
        self.socket2remote = {}
        self.socket2hostintf = {}


    def hostintf2addr(self, hostintf):
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

        src = self.hostintf2addr(source)
        dst = self.hostintf2addr(destination)

        left = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        right = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # dict to map back to hostname & interface
        self.socket2hostintf[left] = "%s/%s" % (src_router, src_interface)
        self.socket2hostintf[right] = "%s/%s" % (dst_router, dst_interface)

        try:
            left.connect(src)
        except:
            self.logger.info("Unable to connect to %s" % self.socket2hostintf[left])
        try:
            right.connect(dst)
        except:
            self.logger.info("Unable to connect to %s" % self.socket2hostintf[right])

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
                try:
                    buf = i.recv(2048)
                except ConnectionResetError:
                    self.logger.warning("connection dropped, reconnecting to source %s" % self.socket2hostintf[i])
                    try:
                        i.connect(self.hostintf2addr(self.socket2hostintf[i]))
                    except:
                        self.logger.warning("reconnect failed, retrying on next spin")
                        continue
                except OSError:
                    self.logger.warning("endpoint not connecting, connecting to source %s" % self.socket2hostintf[i])
                    try:
                        i.connect(self.hostintf2addr(self.socket2hostintf[i]))
                    except:
                        self.logger.warning("connect failed, retrying on next spin")
                        continue

                if len(buf) == 0:
                    return
                self.logger.debug("%05d bytes %s -> %s " % (len(buf), self.socket2hostintf[i], self.socket2hostintf[remote]))
                try:
                    remote.send(buf)
                except BrokenPipeError:
                    self.logger.warning("unable to send packet %05d bytes %s -> %s due to remote being down, trying reconnect" % (len(buf), self.socket2hostintf[i], self.socket2hostintf[remote]))
                    try:
                        remote.connect(self.hostintf2addr(self.socket2hostintf[remote]))
                    except:
                        self.logger.warning("connect failed, retrying on next spin")
                        continue

class NoVR(Exception):
    """ No virtual router
    """
            

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action="store_true", default=False, help='enable debug')
    parser.add_argument('--p2p', nargs='+', help='point-to-point link')
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    tt = TcpBridge()
    for p2p in args.p2p:
        try:
            tt.add_p2p(p2p)
        except NoVR as exc:
            print(exc, " Is it started and did you link it?")
            sys.exit(1)
    tt.work()
