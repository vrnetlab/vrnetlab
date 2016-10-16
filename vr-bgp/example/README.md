vr-bgp example
==============
This is an example showing how vr-bgp can be used in your CI environment to
verify your BGP routing policy.

The example makes use of an Cisco XRv router so make sure you have built the
vr-xrv container (we use version 6.0.1 but you should be able to use older ones
as well).

`start.sh` runs the docker commands to start vr-xrv, which we call xr1, then
start up six vr-bgp instances which will simulate two customers (bgp-cust1 &
bgp-cust2), two peers (bgp-peer1 & bgp-peer2) and two transits (bgp-transit1 &
bgp-transit2). vr-xcon is then used to connect it all together.

`test.py` is the actual test script. It is based on the standard unittest
library in Python but have a couple of different helper functions to glue it
together with the vr-bgp speakers.

The overall policy is fairly simple, we should announce customers to peers &
transit while peers, transit and customers are announced to customers.
Inversely, peers should not be announced to other peers nor to transits. The
different tests in test.py script will test exactly this.

We use the following router-ids:

    10.100.0.0/16           router-IDs
        10.100.1.0/24       router-IDs for customers
            10.100.1.1      cust1
            10.100.1.2      cust2
        10.100.2.0/24       router-IDs for peers
            10.100.2.1      peer1
            10.100.2.2      peer2
        10.100.3.0/24       router-IDs for transits
            10.100.3.1      transit1
            10.100.3.2      transit2

And here are the link networks:

    10.101.0.0/16               link networks
        10.101.1.0/24           link networks for customers
            10.101.1.0/30       DUT <-> cust1
                10.101.1.1      cust1
                10.101.1.2      DUT
            10.101.1.4/30       DUT <-> cust2
                10.101.1.5      cust2
                10.101.1.6      DUT
        10.101.2.0/24           link networks for peers
            10.101.2.0/30       DUT <-> peer1
                10.101.2.1      peer1
                10.101.2.2      DUT
            10.101.2.4/30       DUT <-> peer2
                10.101.2.5      peer2
                10.101.2.6      DUT
        10.101.3.0/24           link networks for transits
            10.101.3.0/30       DUT <-> transit1
                10.101.3.1      transit1
                10.101.3.2      DUT
            10.101.3.4/30       DUT <-> transit2
                10.101.3.5      transit2
                10.101.3.6      DUT

You need to configure the XR router yourself. An example configuration is
included in the file xr-config.txt

Start the whole thing by executing the `start.sh` script. If you are not using
XR 6.0.1 you need to first edit the script and change the version of vr-xrv
used. Wait for the XR router to start (check the serial console). Once up,
apply the configuration and you should be able to see that all BGP sessions
become established;

```
RP/0/0/CPU0:ios#sh bgp ipv4 un sum
Sun Oct 16 13:02:20.671 UTC
BGP router identifier 1.2.3.4, local AS number 2792
BGP generic scan interval 60 secs
Non-stop routing is enabled
BGP table state: Active
Table ID: 0xe0000000   RD version: 30
BGP main routing table version 30
BGP NSR Initial initsync version 3 (Reached)
BGP NSR/ISSU Sync-Group versions 0/0
BGP scan interval 60 secs

BGP is operating in STANDALONE mode.


Process       RcvTblVer   bRIB/RIB   LabelVer  ImportVer  SendTblVer  StandbyVer
Speaker              30         30         30         30          30           0

Neighbor        Spk    AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.101.1.1        0 65011      45      66       30    0    0 00:24:54          1
10.101.1.5        0 65012      46      65       30    0    0 00:24:25          1
10.101.2.1        0 65021      39      44       30    0    0 00:24:19          1
10.101.2.5        0 65022      43      47       30    0    0 00:24:25          1
10.101.3.1        0 65031      43      63       30    0    0 00:24:03          1
10.101.3.5        0 65032      38      60       30    0    0 00:23:57          1

RP/0/0/CPU0:ios#
```

Now run `test.py` and you should get something like this:
```
kll@htpc:~/vrnetlab/vr-bgp/example$ ./test.py
test_bgp101 (__main__.BgpTest)
bgp-cust1 should see bgp-cust2, bgp-peer1, bgp-peer2, bgp-transit1 and bgp-transit2 ... ok
test_bgp102 (__main__.BgpTest)
bgp-cust2 should see bgp-cust1, bgp-peer1, bgp-peer2, bgp-transit1 and bgp-transit2 ... ok
test_bgp103 (__main__.BgpTest)
bgp-peer1 should see bgp-cust1, bgp-cust2 ... ok
test_bgp104 (__main__.BgpTest)
bgp-peer2 should see bgp-cust1, bgp-cust2 ... ok
test_bgp105 (__main__.BgpTest)
bgp-transit1 should see bgp-cust1, bgp-cust2 ... ok
test_bgp106 (__main__.BgpTest)
bgp-transit2 should see bgp-cust1, bgp-cust2 ... ok
test_bgp201 (__main__.BgpTest)
peer1 should not see peer2, transit1, transit2 ... ok
test_bgp202 (__main__.BgpTest)
peer2 should not see peer1, transit1, transit2 ... ok
test_bgp203 (__main__.BgpTest)
transit1 should not see peer1, peer2, transit2 ... ok
test_bgp204 (__main__.BgpTest)
transit2 should not see peer1, peer2, transit1 ... ok
test_bgp205 (__main__.BgpTest)
customer bogon filtering, peer1 should not see customer1 bogon ... ok

----------------------------------------------------------------------
Ran 11 tests in 2.292s

OK
```

It's common that it takes some time for BGP convergence to settle so the first
test run might be retried (the test.py will automatically retry a test up to 10
times with an exponential back-off timer).
