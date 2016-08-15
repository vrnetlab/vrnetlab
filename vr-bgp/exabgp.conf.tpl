group test {
    neighbor {{config.NEIGHBOR}} {
        router-id {{config.ROUTER_ID}};
        local-address {{config.LOCAL_ADDRESS}};
        local-as {{config.LOCAL_AS}};
        peer-as {{config.PEER_AS}};

    }

    process bgpapi {
        parse-routes;
        peer-updates;
        run /bgpapi.py;
    }
}
