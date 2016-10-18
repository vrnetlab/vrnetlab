#!/usr/bin/env python3

import datetime
import json
import logging
import sys
import time
import unittest
import urllib.request
from functools import wraps

all_speakers = [
	'bgp-cust1',
	'bgp-cust2',
	'bgp-peer1',
	'bgp-peer2',
	'bgp-transit1',
	'bgp-transit2'
]
speaker_containers = {}

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry





def docker_inspect(name):
    """ Return inspection information about a running docker container
    """
    container_name = speaker_containers[name]
    if not container_name:
        raise Exception("Couldn't map %s" % name)
    import subprocess
    out = subprocess.check_output(["docker", "inspect", container_name])
    return json.loads(out.decode())


def docker_ip(name):
    """ Return IP address of docker container
    """
    return docker_inspect(name)[0]['NetworkSettings']['IPAddress']


def announce(speaker, routes):
    ip = docker_ip(speaker)
    route_data = { 'routes': routes }
    params = json.dumps(route_data).encode()
    url = "http://%s:5000/announce" % ip
    req = urllib.request.Request(url, data=params, headers={'content-type': 'application/json'})
    response = urllib.request.urlopen(req)



def received(speaker, afi='ipv4 unicast'):
    ip = docker_ip(speaker)
    url = "http://%s:5000/received" % ip
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode())
    if afi not in data:
        return {}
    afi_data = data[afi]
    return afi_data


def get_neighbors(speaker):
    ip = docker_ip(speaker)
    url = "http://%s:5000/neighbors" % ip
    response = urllib.request.urlopen(url)
    return json.loads(response.read().decode())



def wait_for_speakers(speakers, timeout=300):
    """ Wait for BGP speakers to start
    """
    log = logging.getLogger()
    i = 0
    while i < timeout:
        # assume up until proven otherwise
        all_up = True
        for speaker in speakers:
            try:
                neighbors = get_neighbors(speaker)
            except:
                log.debug("BGP speaker %s not up" % speaker)
                all_up = False
                break

        if all_up:
            log.debug("All speakers are up!")
            return

        time.sleep(1)
        i += 1
    raise Exception("timed out")


def wait_for_bgp(speakers, timeout=300):
    """ Wait for all BGP speakers to establish their BGP sessions
    """
    log = logging.getLogger()
    i = 0
    while i < timeout:
        # assume up until proven otherwise
        all_up = True
        for speaker in speakers:
            try:
                neighbors = get_neighbors(speaker)
            except:
                log.debug("BGP speaker %s not up" % speaker)
                all_up = False
                break

            if len(neighbors) == 0:
                all_up = False
            for neighbor, data in neighbors.items():
                if data['state'] != 'up':
                    log.debug("BGP speaker %s session not up" % speaker)
                    all_up = False
                else:
                    # convert timestamp to datetime object
                    ts = datetime.datetime.strptime(data['timestamp'], "%Y-%m-%d %H:%M:%S")
                    # what is delta between now and when peer came up?
                    delta = datetime.datetime.utcnow() - ts
                    # peer must be up for 10 seconds to let it "settle"
                    if delta < datetime.timedelta(seconds=5):
                        log.debug("BGP speaker %s session not up long enough" % speaker)
                        all_up = False
        if all_up:
            log.debug("All BGP speaker sessions are up!")
            return

        time.sleep(1)
        i += 1
    raise Exception("timed out")





class BgpTest(unittest.TestCase):
    def setUp(self):
        # wait for bgp sessions to establish
        wait_for_speakers(all_speakers)

        # tell vr-bgp speakers to announce routes

        # customer announcements
        cust1_announce = [
                { 'prefix': '11.0.0.0/24' }, # normal
                { 'prefix': '11.1.0.0/24', 'community': [ '65000:0' ] }, # do not announce to peers/transit
                { 'prefix': '10.0.11.0/24' } # 10.0.11.0/24 is BOGON and should be filtered
            ]

        announce('bgp-cust1', cust1_announce)
        cust2_announce = [
                { 'prefix': '12.0.0.0/24' },
                { 'prefix': '10.0.12.0/24' }
            ]
        announce('bgp-cust2', cust2_announce)

        # peer announcements
        peer1_announce = [
                { 'prefix': '21.0.0.0/24', 'community': [ '2792:10300' ] } # fake we are customer - must be stripped
            ]
        announce('bgp-peer1', peer1_announce)
        peer2_announce = [
                { 'prefix': '22.0.0.0/24' }
            ]
        announce('bgp-peer2', peer2_announce)

        # transit announcements
        tran1_announce = [
                { 'prefix': '31.0.0.0/24', 'community': [ '2792:10300'] } # fake we are customer - must be stripped
            ]
        announce('bgp-transit1', tran1_announce)
        tran2_announce = [
                { 'prefix': '32.0.0.0/24' }
            ]
        announce('bgp-transit2', tran2_announce)

        wait_for_bgp(all_speakers)


    # start off with "positive" tests, i.e. where we check for the presence of
    # prefixes. see test_bgp2xx for "negative" tests

    @retry(AssertionError, tries=10)
    def test_bgp101(self):
        """ bgp-cust1 should see bgp-cust2, bgp-peer1, bgp-peer2, bgp-transit1 and bgp-transit2
        """
        rec = received('bgp-cust1')
        self.assertIn('12.0.0.0/24', rec)
        self.assertIn('21.0.0.0/24', rec)
        self.assertIn('22.0.0.0/24', rec)
        self.assertIn('31.0.0.0/24', rec)
        self.assertIn('32.0.0.0/24', rec)


    @retry(AssertionError, tries=10)
    def test_bgp102(self):
        """ bgp-cust2 should see bgp-cust1, bgp-peer1, bgp-peer2, bgp-transit1 and bgp-transit2
        """
        rec = received('bgp-cust2')
        self.assertIn('11.0.0.0/24', rec)
        self.assertIn('21.0.0.0/24', rec)
        self.assertIn('22.0.0.0/24', rec)
        self.assertIn('31.0.0.0/24', rec)
        self.assertIn('32.0.0.0/24', rec)


    @retry(AssertionError, tries=10)
    def test_bgp103(self):
        """ bgp-peer1 should see bgp-cust1, bgp-cust2
        """
        rec = received('bgp-peer1')
        self.assertIn('11.0.0.0/24', rec)
        self.assertIn('12.0.0.0/24', rec)


    @retry(AssertionError, tries=10)
    def test_bgp104(self):
        """ bgp-peer2 should see bgp-cust1, bgp-cust2
        """
        rec = received('bgp-peer2')
        self.assertIn('11.0.0.0/24', rec)
        self.assertIn('12.0.0.0/24', rec)


    @retry(AssertionError, tries=10)
    def test_bgp105(self):
        """ bgp-transit1 should see bgp-cust1, bgp-cust2
        """
        rec = received('bgp-transit1')
        self.assertIn('11.0.0.0/24', rec)
        self.assertIn('12.0.0.0/24', rec)


    @retry(AssertionError, tries=10)
    def test_bgp106(self):
        """ bgp-transit2 should see bgp-cust1, bgp-cust2
        """
        rec = received('bgp-transit2')
        self.assertIn('11.0.0.0/24', rec)
        self.assertIn('12.0.0.0/24', rec)




    # "negative" tests (i.e. we don't see a particular prefix) are run after,
    # to make sure we don't catch the peers in the early phases when they
    # haven't announced everything

    @retry(AssertionError, tries=10)
    def test_bgp201(self):
        """ peer1 should not see peer2, transit1, transit2
        """
        rec = received('bgp-peer1')
        self.assertNotIn('22.0.0.0/24', rec)
        self.assertNotIn('31.0.0.0/24', rec)
        self.assertNotIn('32.0.0.0/24', rec)

    @retry(AssertionError, tries=10)
    def test_bgp202(self):
        """ peer2 should not see peer1, transit1, transit2
        """
        rec = received('bgp-peer2')
        self.assertNotIn('21.0.0.0/24', rec)
        self.assertNotIn('31.0.0.0/24', rec)
        self.assertNotIn('32.0.0.0/24', rec)

    @retry(AssertionError, tries=10)
    def test_bgp203(self):
        """ transit1 should not see peer1, peer2, transit2
        """
        rec = received('bgp-transit1')
        self.assertNotIn('21.0.0.0/24', rec)
        self.assertNotIn('22.0.0.0/24', rec)
        self.assertNotIn('32.0.0.0/24', rec)

    @retry(AssertionError, tries=10)
    def test_bgp204(self):
        """ transit2 should not see peer1, peer2, transit1
        """
        rec = received('bgp-transit2')
        self.assertNotIn('21.0.0.0/24', rec)
        self.assertNotIn('22.0.0.0/24', rec)
        self.assertNotIn('31.0.0.0/24', rec)

    @retry(AssertionError, tries=10)
    def test_bgp205(self):
        """ customer bogon filtering, peer1 should not see customer1 bogon
        """
        rec = received('bgp-peer1')
        self.assertNotIn('10.0.11.0/24', rec)

    @retry(AssertionError, tries=10)
    def test_bgp206(self):
        """ peer1 should not see cust1 prefix with control community
        """
        rec = received('bgp-peer1')
        self.assertNotIn('11.1.0.0/24', rec)



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--wait-for-speakers', action='store_true')
    parser.add_argument('--wait-for-bgp-up', action='store_true')
    parser.add_argument('--bgp-cust1', default="bgp-cust1")
    parser.add_argument('--bgp-cust2', default="bgp-cust2")
    parser.add_argument('--bgp-peer1', default="bgp-peer1")
    parser.add_argument('--bgp-peer2', default="bgp-peer2")
    parser.add_argument('--bgp-transit1', default="bgp-transit1")
    parser.add_argument('--bgp-transit2', default="bgp-transit2")
    args, rest = parser.parse_known_args()

    speaker_containers['bgp-peer1'] = args.bgp_peer1
    speaker_containers['bgp-peer2'] = args.bgp_peer2
    speaker_containers['bgp-cust1'] = args.bgp_cust1
    speaker_containers['bgp-cust2'] = args.bgp_cust2
    speaker_containers['bgp-transit1'] = args.bgp_transit1
    speaker_containers['bgp-transit2'] = args.bgp_transit2

    # set up logging
    log = logging.getLogger()
    logging.basicConfig()
    log.setLevel(logging.INFO)

    if args.debug:
        log.setLevel(logging.DEBUG)

    if args.wait_for_speakers:
        wait_for_speakers(all_speakers)
        sys.exit(0)

    if args.wait_for_bgp_up:
        wait_for_bgp(all_speakers)
        sys.exit(0)

    sys.argv[1:] = rest

    unittest.main(verbosity=2)
