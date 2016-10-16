# start XR virtual router
docker run --name xr1 --privileged -i -t -d vr-xrv:6.0.1

# start vr-bgp and vr-xcon to connect it all together
docker rm -f bgp-cust1 bgp-cust2 bgp-peer1 bgp-peer2 bgp-transit1 bgp-transit2 bgp-xcon
docker run --name bgp-cust1 --privileged -i -t -d vr-bgp --router-id 10.100.1.1 --ipv4-prefix 10.101.1.0/30 --local-as 65011 --peer-as 2792
docker run --name bgp-cust2 --privileged -i -t -d vr-bgp --router-id 10.100.1.2 --ipv4-prefix 10.101.1.4/30 --local-as 65012 --peer-as 2792
docker run --name bgp-peer1 --privileged -i -t -d vr-bgp --router-id 10.100.2.1 --ipv4-prefix 10.101.2.0/30 --local-as 65021 --peer-as 2792
docker run --name bgp-peer2 --privileged -i -t -d vr-bgp --router-id 10.100.2.2 --ipv4-prefix 10.101.2.4/30 --local-as 65022 --peer-as 2792
docker run --name bgp-transit1 --privileged -i -t -d vr-bgp --router-id 10.100.3.1 --ipv4-prefix 10.101.3.0/30 --local-as 65031 --peer-as 2792
docker run --name bgp-transit2 --privileged -i -t -d vr-bgp --router-id 10.100.3.2 --ipv4-prefix 10.101.3.4/30 --local-as 65032 --peer-as 2792
docker run --name bgp-xcon --privileged -i -t -d --link bgp-cust1 --link bgp-cust2 --link bgp-peer1 --link bgp-peer2 --link bgp-transit1 --link bgp-transit2 --link xr1 vr-xcon --p2p xr1/1--bgp-cust1/1 xr1/2--bgp-cust2/1 xr1/3--bgp-peer1/1 xr1/4--bgp-peer2/1 xr1/5--bgp-transit1/1 xr1/6--bgp-transit2/1 --debug
