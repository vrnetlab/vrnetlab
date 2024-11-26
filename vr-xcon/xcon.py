#!/usr/bin/env python3

import fcntl
import ipaddress
import logging
import os
import select
import signal
import socket
import _socket
import struct
import subprocess
import sys
import time


def handle_SIGCHLD(signal, frame):
    os.waitpid(-1, os.WNOHANG)

def handle_SIGTERM(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, handle_SIGTERM)
signal.signal(signal.SIGTERM, handle_SIGTERM)
signal.signal(signal.SIGCHLD, handle_SIGCHLD)


class EndpointSocket(socket.socket):
    def __init__(self, endpoint, *args, **kwargs):
        super(EndpointSocket, self).__init__(*args, **kwargs)
        self.endpoint = endpoint

    @classmethod
    def copy(cls, sock):
        fd = _socket.dup(sock.fileno())
        copy = cls(sock.family, sock.type, sock.proto, fileno=fd)
        copy.settimeout(sock.gettimeout())
        return copy

    @property
    def address(self):
        hostname, interface = self.endpoint.split("/")
        try:
            res = socket.getaddrinfo(hostname, "100%02d" % int(interface), socket.AF_INET)
        except socket.gaierror:
            raise NoVR("Unable to resolve %s" % hostname)
        sockaddr = res[0][4]
        return sockaddr


class Tcp2Raw:
    def __init__(self, raw_intf = 'eth1', listen_port=10001):
        self.logger = logging.getLogger()
        # setup TCP side
        self.s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.s.bind(('::0', listen_port))
        self.s.listen(1)
        self.tcp = None

        # track current state of TCP side tunnel. 0 = reading size, 1 = reading packet
        self.tcp_state = 0
        self.tcp_buf = b''
        self.tcp_remaining = 0

        # setup raw side
        self.raw = socket.socket( socket.AF_PACKET , socket.SOCK_RAW , socket.ntohs(0x0003))
        self.raw.bind((raw_intf, 0))
        # don't block
        self.raw.setblocking(0)


    def work(self):
        while True:

            skts = [self.s, self.raw]
            if self.tcp is not None:
                skts.append(self.tcp)
            ir = select.select(skts,[],[])[0][0]
            if ir == self.s:
                self.logger.debug("received incoming TCP connection, setting up!")
                self.tcp, addr = self.s.accept()
            elif ir == self.tcp:
                self.logger.debug("received packet from TCP and sending to raw interface")

                try:
                    buf = ir.recv(2048)
                except (ConnectionResetError, OSError):
                    self.logger.warning("connection dropped")
                    continue

                if len(buf) == 0:
                    self.logger.info("no data from TCP socket, assuming client hung up, closing our socket")
                    ir.close()
                    self.tcp = None
                    self.tcp_state = 0
                    self.tcp_buf = b''
                    self.tcp_remaining = 0
                    continue

                self.tcp_buf += buf
                self.logger.debug("read %d bytes from tcp, tcp_buf length %d" % (len(buf), len(self.tcp_buf)))
                while True:
                    if self.tcp_state == 0:
                        # we want to read the size, which is 4 bytes, if we
                        # don't have enough bytes wait for the next spin
                        if not len(self.tcp_buf) > 4:
                            self.logger.debug("reading size - less than 4 bytes available in buf; waiting for next spin")
                            break
                        size = socket.ntohl(struct.unpack("I", self.tcp_buf[:4])[0]) # first 4 bytes is size of packet
                        self.tcp_buf = self.tcp_buf[4:] # remove first 4 bytes of buf
                        self.tcp_remaining = size
                        self.tcp_state = 1
                        self.logger.debug("reading size - pkt size: %d" % self.tcp_remaining)

                    if self.tcp_state == 1: # read packet data
                        # we want to read the whole packet, which is specified
                        # by tcp_remaining, if we don't have enough bytes we
                        # wait for the next spin
                        if len(self.tcp_buf) < self.tcp_remaining:
                            self.logger.debug("reading packet - less than remaining bytes; waiting for next spin")
                            break
                        self.logger.debug("reading packet - reading %d bytes" % self.tcp_remaining)
                        payload = self.tcp_buf[:self.tcp_remaining]
                        self.tcp_buf = self.tcp_buf[self.tcp_remaining:]
                        self.tcp_remaining = 0
                        self.tcp_state = 0
                        self.raw.send(payload)

            else:
                # we always get full packets from the raw interface
                payload = self.raw.recv(2048)
                buf = struct.pack("I", socket.htonl(len(payload))) + payload
                if self.tcp is None:
                    self.logger.warning("received packet from raw interface but TCP not connected, discarding packet")
                else:
                    self.logger.debug("received packet from raw interface and sending to TCP")
                    try:
                        self.tcp.send(buf)
                    except:
                        self.logger.warning("could not send packet to TCP session")


class Tcp2Tap:
    def __init__(self, tap_intf = 'tap0', listen_port=10001):
        self.logger = logging.getLogger()
        # setup TCP side
        self.s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.s.bind(('::0', listen_port))
        self.s.listen(1)
        self.tcp = None

        # track current state of TCP side tunnel. 0 = reading size, 1 = reading packet
        self.tcp_state = 0
        self.tcp_buf = b''
        self.tcp_remaining = 0

        # setup tap side
        TUNSETIFF = 0x400454ca
        IFF_TUN = 0x0001
        IFF_TAP = 0x0002
        IFF_NO_PI = 0x1000
        self.tap = os.open("/dev/net/tun", os.O_RDWR)
        # we want a tap interface, no packet info and it should be called tap0
        # TODO: implement dynamic name using tap%d, right now we assume we are
        # only program in this namespace (docker container) that creates tap0
        ifs = fcntl.ioctl(self.tap, TUNSETIFF, struct.pack("16sH", tap_intf.encode(), IFF_TAP | IFF_NO_PI))
        # ifname - good for when we do dynamic interface name
        ifname = ifs[:16].decode().strip("\x00")


    def work(self):
        while True:
            skts = [self.s, self.tap]
            if self.tcp is not None:
                skts.append(self.tcp)
            ir = select.select(skts,[],[])[0][0]
            if ir == self.s:
                self.logger.debug("received incoming TCP connection, setting up!")
                self.tcp, addr = self.s.accept()
            elif ir == self.tcp:
                self.logger.debug("received packet from TCP and sending to tap interface")

                try:
                    buf = ir.recv(2048)
                except (ConnectionResetError, OSError):
                    self.logger.warning("connection dropped")
                    continue

                if len(buf) == 0:
                    self.logger.info("no data from TCP socket, assuming client hung up, closing our socket")
                    ir.close()
                    self.tcp = None
                    self.tcp_state = 0
                    self.tcp_buf = b''
                    self.tcp_remaining = 0
                    continue

                self.tcp_buf += buf
                self.logger.debug("read %d bytes from tcp, tcp_buf length %d" % (len(buf), len(self.tcp_buf)))
                while True:
                    if self.tcp_state == 0:
                        # we want to read the size, which is 4 bytes, if we
                        # don't have enough bytes wait for the next spin
                        if not len(self.tcp_buf) > 4:
                            self.logger.debug("reading size - less than 4 bytes available in buf; waiting for next spin")
                            break
                        size = socket.ntohl(struct.unpack("I", self.tcp_buf[:4])[0]) # first 4 bytes is size of packet
                        self.tcp_buf = self.tcp_buf[4:] # remove first 4 bytes of buf
                        self.tcp_remaining = size
                        self.tcp_state = 1
                        self.logger.debug("reading size - pkt size: %d" % self.tcp_remaining)

                    if self.tcp_state == 1: # read packet data
                        # we want to read the whole packet, which is specified
                        # by tcp_remaining, if we don't have enough bytes we
                        # wait for the next spin
                        if len(self.tcp_buf) < self.tcp_remaining:
                            self.logger.debug("reading packet - less than remaining bytes; waiting for next spin")
                            break
                        self.logger.debug("reading packet - reading %d bytes" % self.tcp_remaining)
                        payload = self.tcp_buf[:self.tcp_remaining]
                        self.tcp_buf = self.tcp_buf[self.tcp_remaining:]
                        self.tcp_remaining = 0
                        self.tcp_state = 0
                        os.write(self.tap, payload)

            else:
                # we always get full packets from the tap interface
                payload = os.read(self.tap, 2048)
                buf = struct.pack("I", socket.htonl(len(payload))) + payload
                if self.tcp is None:
                    self.logger.warning("received packet from tap interface but TCP not connected, discarding packet")
                else:
                    self.logger.debug("received packet from tap interface and sending to TCP")
                    try:
                        self.tcp.send(buf)
                    except:
                        self.logger.warning("could not send packet to TCP session")



class TcpBridge:
    def __init__(self):
        self.logger = logging.getLogger()
        self.sockets = []
        self.socket2remote = {}
        self.socket2hostintf = {}


    def hostintf2addr(self, hostintf):
        hostname, interface = hostintf.split("/")

        try:
            res = socket.getaddrinfo(hostname, "100%02d" % int(interface), socket.AF_INET)
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
                except ConnectionResetError as exc:
                    self.logger.warning("connection dropped, reconnecting to source %s" % self.socket2hostintf[i])
                    try:
                        i.connect(self.hostintf2addr(self.socket2hostintf[i]))
                        self.logger.debug("reconnect to %s successful" % self.socket2hostintf[i])
                    except Exception as exc:
                        self.logger.warning("reconnect failed %s" % str(exc))
                    continue
                except OSError as exc:
                    self.logger.warning("endpoint not connected, connecting to source %s" % self.socket2hostintf[i])
                    try:
                        i.connect(self.hostintf2addr(self.socket2hostintf[i]))
                        self.logger.debug("connect to %s successful" % self.socket2hostintf[i])
                    except:
                        self.logger.warning("connect failed %s" % str(exc))
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
                        self.logger.debug("connect to %s successful" % self.socket2hostintf[remote])
                    except Exception as exc:
                        self.logger.warning("connect failed %s" % str(exc))
                    continue


class TcpHub:
    def __init__(self):
        self.logger = logging.getLogger()
        self.sockets = []

    def add_ep(self, endpoint):
        s = EndpointSocket(endpoint)
        try:
            s.connect(s.address)
        except:
            self.logger.info("unable to connect to %s" % s.endpoint)
        s.setblocking(False)
        self.sockets.append(s)

    def re_connect(self, s):
        endpoint = s.endpoint
        self.logger.info("re-connecting to %s ..." % endpoint)
        s.close()

        # cannot remove socket from the list normally as its __repr__() changes
        # when the socket is closed
        for i, t in enumerate(self.sockets):
            if t.endpoint == endpoint:
                del self.sockets[i]
                break

        self.add_ep(endpoint)

    def work(self):
        while True:
            try:
                ir,_,_ = select.select(self.sockets, [], [])
            except select.error as exc:
                self.logger.critical("select failed %s" % str(exc))
                break

            for i in ir:
                try:
                    buf = i.recv(2048)
                except (ConnectionError, OSError):
                    self.logger.warning("connection error while reading from %s" % i.endpoint)
                    self.re_connect(i)
                if len(buf) == 0:
                    self.logger.warning("empty buffer for %s" % i.endpoint)
                    self.re_connect(i)

                # send to all other sockets
                for remote in self.sockets:
                    # don't need to send to ourselves though
                    if i is remote:
                        continue

                    self.logger.debug("%05d bytes %s -> %s " % (len(buf), i.endpoint, remote.endpoint))
                    try:
                        remote.send(buf)
                    except (ConnectionError, OSError):
                        self.logger.warning("unable to send packet %05d bytes %s -> %s due to remote being down" % (len(buf), i.endpoint, remote.endpoint))
                        self.re_connect(remote)


class NoVR(Exception):
    """ No virtual router
    """

class TapConfigurator(object):
    def __init__(self, logger):
        self.logger = logger

    def _configure_interface_address(self, interface, address, default_route=None):
        next_hop = None
        net = ipaddress.ip_interface(address)
        if default_route:
            try:
                next_hop = ipaddress.ip_address(default_route)
            except ValueError:
                self.logger.error("next-hop address {} could not be parsed".format(default_route))
                sys.exit(1)

        if default_route and next_hop not in net.network:
            self.logger.error("next-hop address {} not in network {}".format(next_hop, net))
            sys.exit(1)

        subprocess.check_call(["ip", "-{}".format(net.version), "address", "add", str(net.ip) + "/" + str(net.network.prefixlen), "dev", interface])
        if next_hop:
            try:
                subprocess.check_call(["ip", "-{}".format(net.version), "route", "del", "default"])
            except:
                pass
            subprocess.check_call(["ip", "-{}".format(net.version), "route", "add", "default", "dev", interface, "via", str(next_hop)])


    def configure_interface(self, interface='tap0', vlan=None,
                            ipv4_address=None, ipv4_route=None,
                            ipv6_address=None, ipv6_route=None):
        # enable the interface
        subprocess.check_call(["ip", "link", "set", interface, "up"])

        interface_sysctl = interface
        if vlan:
            physical_interface = interface
            interface_sysctl = '{}/{}'.format(interface, vlan)
            interface = '{}.{}'.format(interface, vlan)
            subprocess.check_call(["ip", "link", "add", "link", physical_interface, "name",
                                   interface, "type", "vlan", "id", str(vlan)])
            subprocess.check_call(["ip", "link", "set", interface, "up"])

        if ipv4_address:
            self._configure_interface_address(interface, ipv4_address, ipv4_route)

        if ipv6_address:
            # stupid hack for docker engine disabling IPv6. It's somewhere around
            # version 17.04 that docker engine started disabling ipv6 on the sysctl
            # net.ipv6.conf.all and net.ipv6.conf.default while eth0 and lo still has
            # it, if docker engine is started with --ipv6. However, with the default at
            # disable we have to specifically enable it for interfaces created after the
            # container started...
            subprocess.check_call(["sysctl", "net.ipv6.conf.{}.disable_ipv6=0".format(interface_sysctl)])
            self._configure_interface_address(interface, ipv6_address, ipv6_route)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action="store_true", default=False, help='enable debug')
    meg = parser.add_mutually_exclusive_group(required=True)
    meg.add_argument('--p2p', nargs='+', help='point-to-point link between virtual routers')
    meg.add_argument('--hub', nargs='+', help='hub between virtual routers, will forward any incoming packets to all outputs, like a hub')
    meg.add_argument('--raw-listen', help='raw to virtual router. Will listen on specified port for incoming connection; 1 for TCP/10001')
    meg.add_argument('--tap-listen', help='tap to virtual router. Will listen on specified port for incoming connection; 1 for TCP/10001')
    raw = parser.add_argument_group('raw')
    raw.add_argument('--raw-if', default="eth1", help='name of raw interface (use with other --raw-* arguments)')
    tap = parser.add_argument_group('tap')
    tap.add_argument('--tap-if', default="tap0", help='name of tap interface (use with other --tap-* arguments)')
    tap.add_argument('--ipv4-address', help='IPv4 address to use on the tap interface')
    tap.add_argument('--ipv4-route', help='default IPv4 route to use on the tap interface')
    tap.add_argument('--ipv6-address', help='IPv6 address to use on the tap interface')
    tap.add_argument('--ipv6-route', help='default IPv6 route to use on the tap interface')
    tap.add_argument('--vlan', type=int, help='VLAN ID to use on the tap interface')
    parser.add_argument('--trace', action="store_true", help="dummy, we don't support tracing but taking the option makes vrnetlab containers uniform")
    args = parser.parse_args()

    LOG_FORMAT = "%(asctime)s: %(module)-10s %(levelname)-8s %(message)s"
    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Fake healtcheck until supported in xcon.py
    with open("health", "w") as hc:
        hc.write("0")

    if args.p2p:
        tt = TcpBridge()
        for p2p in args.p2p:
            try:
                tt.add_p2p(p2p)
            except NoVR as exc:
                print(exc, " Is it started and did you link it?")
                sys.exit(1)
        tt.work()

    if args.hub:
        hub = TcpHub()
        for ep in args.hub:
            try:
                hub.add_ep(ep)
            except NoVR as exc:
                print(exc, " Is it started and did you link it?")
                sys.exit(1)
        hub.work()

    if args.tap_listen:
        # init Tcp2Tap to create interface
        t2t = Tcp2Tap(args.tap_if, 10000 + int(args.tap_listen))

        # now (optionally) configure addressing
        tc = TapConfigurator(logger)
        tc.configure_interface(interface=args.tap_if, vlan=args.vlan,
                               ipv4_address=args.ipv4_address, ipv4_route=args.ipv4_route,
                               ipv6_address=args.ipv6_address, ipv6_route=args.ipv6_route)
        t2t.work()

    if args.raw_listen:
        while True:
            try:
                t2r = Tcp2Raw(args.raw_if, 10000 + int(args.raw_listen))
                t2r.work()
            except Exception as exc:
                print(exc)
            time.sleep(1)
