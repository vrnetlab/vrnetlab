vr-bgp example
==============
This is an example showing how vr-bgp can be used in your CI environment to
verify your BGP routing policy.

The example makes use of a Juniper vMX router so make sure you have built the
vr-vmx container (we use version 16.1R1.6 but you should be able to use older ones
as well).

`start.sh` runs the docker commands to start vr-vmx, which we call j1, then
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

You need to configure the vMX router yourself. An example configuration is
included in the file junos-config.txt

Start the whole thing by executing the `start.sh` script. If you are not using
vMX 16.1R1.7 you need to first edit the script and change the version of vr-vmx
used. Wait for the vMX router to start (check the serial console). Once up,
apply the configuration and you should be able to see that all BGP sessions
become established;

```
root> show bgp summary
Groups: 6 Peers: 12 Down peers: 6
Table          Tot Paths  Act Paths Suppressed    History Damp State    Pending
inet.0
                       9          7          0          0          0          0
inet6.0
                       0          0          0          0          0          0
Peer                     AS      InPkt     OutPkt    OutQ   Flaps Last Up/Dwn State|#Active/Received/Accepted/Damped...
10.101.1.1            65011         25         27       0       8        9:17 2/3/2/0              0/0/0/0
10.101.1.5            65012         23         29       0       8        9:18 1/2/1/0              0/0/0/0
10.101.2.1            65021         22         25       0       8        9:17 1/1/1/0              0/0/0/0
10.101.2.5            65022         22         25       0       9        9:17 1/1/1/0              0/0/0/0
10.101.3.1            65031         22         24       0       9        9:16 1/1/1/0              0/0/0/0
10.101.3.5            65032         22         24       0       8        9:12 1/1/1/0              0/0/0/0
2001:db8::1:1         65011         24         25       0       7        9:12 Establ
  inet6.0: 0/0/0/0
2001:db8::1:5         65012         25         25       0       7        9:13 Establ
  inet6.0: 0/0/0/0
2001:db8::2:1         65021         24         25       0       6        9:14 Establ
  inet6.0: 0/0/0/0
2001:db8::2:5         65022         23         25       0       7        9:17 Establ
  inet6.0: 0/0/0/0
2001:db8::3:1         65031         24         25       0       6        9:14 Establ
  inet6.0: 0/0/0/0
2001:db8::3:5         65032         24         25       0       7        9:19 Establ
  inet6.0: 0/0/0/0
```

Now run `test.py` and you should get something like this:
```
kll@htpc:~/vrnetlab/vr-bgp/example$ ./test.py
test_bgp101 (__main__.BgpTest)
bgp-cust1 should see bgp-cust2, bgp-peer1, bgp-peer2, bgp-transit1 and bgp-transit2 ... '12.0.0.0/24' not found in {}, Retrying in 3 seconds...
ok
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
test_bgp206 (__main__.BgpTest)
peer1 should not see cust1 prefix with control community ... ok

----------------------------------------------------------------------
Ran 12 tests in 5.743s

OK
kll@htpc:~/vrnetlab/vr-bgp/example$
```

We can see that the first test fails which can be rather common as BGP has not
converged yet. Each test is automatically retried up to 10 times with an
exponential back off timer. The tests are ordered such that "positive" tests,
that look for the presence of a prefix, come first while "negative" tests that
look for lack of prefixes come after. The positive tests will be retried until
BGP has converged and we can then be sure about the result of the negative
tests too.
